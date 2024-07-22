# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Contains the implementation of hte DocsHandler, providing the business logic for handling documents."""

import json
import logging
from typing import Literal, NamedTuple

from sms.config import Config
from sms.models import Criteria, DocumentType, UpsertionDetails
from sms.ports.inbound.docs_handler import DocsHandlerPort
from sms.ports.outbound.docs_dao import DocsDaoPort


def log_and_raise_permissions_error(
    db_name: str, collection: str, operation: Literal["read", "write"]
):
    """Log and raise a PermissionError."""
    rule = f"{db_name}.{collection}:{operation[0]}"
    error = PermissionError(
        f"'{operation.title()}' operations not allowed on db '{db_name}',"
        + f" collection '{collection}'. No rule found that matches '{rule}'",
    )
    logging.error(
        error,
        extra={"db_name": db_name, "collection": collection, "operation": operation},
    )
    raise error


class Permission(NamedTuple):
    """Represents one permission specifying the allowed ops on a given collection."""

    db_name: str
    collection: str
    ops: str


class Permissions:
    """A class to parse and interpret configured permissions for database operations."""

    permissions: list[Permission]

    def __init__(self, permissions: list[str]):
        """Set up the permissions parser. Permissions should already by validated by
        the config model.
        """
        self.permissions = []
        for permission in permissions:
            namespace, ops = permission.rsplit(":")
            database, collection = namespace.split(".", 1)
            self.permissions.append(Permission(database, collection, ops))

    def get_permissions(self, db_name, collection_name) -> str:
        """List the operations allowed on the specified collection."""
        for rule in self.permissions:
            if rule.db_name in ("*", db_name) and rule.collection in (
                "*",
                collection_name,
            ):
                return rule.ops
        return ""

    def can_write(self, db_name: str, collection_name: str) -> bool:
        """Check if WRITE operations are allowed on the specified collection."""
        return "w" in self.get_permissions(db_name, collection_name)

    def can_read(self, db_name: str, collection_name: str) -> bool:
        """Check if READ operations are allowed on the specified collection."""
        return "r" in self.get_permissions(db_name, collection_name)


class DocsHandler(DocsHandlerPort):
    """Concrete implementation of a MongoDB Document Handler"""

    def __init__(self, *, config: Config, docs_dao: DocsDaoPort):
        self._prefix = config.db_prefix
        self._permissions = Permissions(permissions=config.db_permissions)
        self._docs_dao = docs_dao

    def _parse_criteria(self, criteria: Criteria) -> Criteria:
        """Parse the criteria, converting any JSON strings to objects."""
        parsed_criteria = {**criteria}
        for key, value in criteria.items():
            if (
                isinstance(value, str)
                and value.startswith("{")
                and value.endswith("}")
                and ":" in value
            ):
                try:
                    parsed_criteria[key] = json.loads(value)
                except json.JSONDecodeError as err:
                    error = self.CriteriaFormatError(key=key)
                    logging.error(
                        error,
                        extra={"key": key, "value": value},
                    )
                    raise error from err
        return parsed_criteria

    async def get(
        self, db_name: str, collection: str, criteria: Criteria
    ) -> list[DocumentType]:
        """Get documents satisfying the criteria.

        Args:
        - `db_name`: The name of the database.
        - `collection`: The name of the collection.
        - `criteria`: The criteria to filter the documents (mapping).

        Raises:
        - `PermissionError`: If the operation is not allowed per configuration.
        - `OperationError`: If the operation fails in the database for any reason.
        - `CriteriaFormatError`: If the filter criteria format is invalid.
        """
        if not self._permissions.can_read(db_name, collection):
            log_and_raise_permissions_error(db_name, collection, "read")

        parsed_criteria = self._parse_criteria(criteria)

        full_db_name = f"{self._prefix}{db_name}"
        try:
            results = await self._docs_dao.get(
                db_name=full_db_name, collection=collection, criteria=parsed_criteria
            )
        except Exception as err:
            error = self.ReadOperationError(criteria=criteria)
            logging.error(error)
            raise error from err

        return results

    async def upsert(
        self, db_name: str, collection: str, upsertion_details: UpsertionDetails
    ) -> None:
        """Insert or update one or more documents.

        Args:
        - `db_name`: The database name.
        - `collection`: The collection name.
        - `upsertion_details`: The details for upserting the documents, which include the
                id_field and the documents to upsert.

        Raises:
        - `PermissionError`: If the operation is not allowed per configuration.
        - `MissingIdFieldError`: If the id_field is missing in any of the documents.
        - `OperationError`: If the operation fails in the database for any reason.
        """
        # Get permissions for collection
        can_write = self._permissions.can_write(db_name, collection)

        if not can_write:
            log_and_raise_permissions_error(db_name, collection, "write")

        # Work with a list
        id_field, documents = upsertion_details.id_field, upsertion_details.documents
        if not isinstance(documents, list):
            documents = [documents]

        # Make sure each doc has the specified id_field
        for doc in documents:
            if id_field not in doc:
                raise self.MissingIdFieldError(id_field=id_field)

        full_db_name = f"{self._prefix}{db_name}"
        try:
            await self._docs_dao.upsert(
                db_name=full_db_name,
                collection=collection,
                id_field=id_field,
                documents=documents,
            )
        except Exception as err:
            error = self.UpsertionError(id_field=id_field)
            logging.error(
                error,
                extra={"documents": documents},
            )
            raise error from err

    async def delete(self, db_name: str, collection: str, criteria: Criteria) -> None:
        """Delete documents satisfying the criteria.

        Args:
        - `db_name`: The name of the database.
        - `collection`: The name of the collection.
        - `criteria`: The criteria to filter the documents (mapping).

        Raises:
        - `PermissionError`: If the operation is not allowed per configuration.
        - `OperationError`: If the operation fails in the database for any reason.
        - `CriteriaFormatError`: If the filter criteria format is invalid.
        """
        if not self._permissions.can_write(db_name, collection):
            log_and_raise_permissions_error(db_name, collection, "write")

        parsed_criteria = self._parse_criteria(criteria)
        full_db_name = f"{self._prefix}{db_name}"

        try:
            await self._docs_dao.delete(
                db_name=full_db_name, collection=collection, criteria=parsed_criteria
            )
        except Exception as err:
            error = self.DeletionError(criteria=criteria)
            logging.error(error)
            raise error from err
