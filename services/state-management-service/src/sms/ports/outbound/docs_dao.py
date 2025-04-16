# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Contains port definition for a Doc Handler"""

from abc import ABC, abstractmethod

from sms.models import Criteria, DocumentType


class DocsDaoPort(ABC):
    """Port definition for a Doc Handler"""

    class DbNotFoundError(RuntimeError):
        """Raised when a database does not exist."""

        def __init__(self, *, db_name: str):
            super().__init__(f"Database '{db_name}' not found.")

    class CollectionNotFoundError(RuntimeError):
        """Raised when a collection does not exist."""

        def __init__(self, *, db_name: str, collection: str):
            super().__init__(f"Collection '{collection}' not found in db '{db_name}'.")

    @abstractmethod
    async def get(
        self, *, db_name: str, collection: str, criteria: Criteria
    ) -> list[DocumentType]:
        """Get documents satisfying the criteria.

        Args:
        - `db_name`: The database name.
        - `collection`: The collection name.
        - `criteria`: The criteria to use for filtering the documents (mapping)

        Raises:
        - `DbNotFoundError`: If the database does not exist.
        - `CollectionNotFoundError`: If the collection does not exist.
        """
        ...

    @abstractmethod
    async def upsert(
        self,
        *,
        db_name: str,
        collection: str,
        id_field: str,
        documents: list[DocumentType],
    ) -> None:
        """Insert or update one or more documents.

        Args:
        - `db_name`: The database name.
        - `collection`: The collection name.
        - `id_field`: The field to use as the document id, which must be present on each doc.
        - `documents`: A list of the documents to upsert.
        """
        ...

    @abstractmethod
    async def delete(
        self, *, db_name: str, collection: str, criteria: Criteria
    ) -> None:
        """Delete documents satisfying the criteria.

        No error is raised if the db or collection does not exist.

        Args:
        - `db_name`: The database name.
        - `collection`: The collection name.
        - `criteria`: The criteria to use for filtering the documents (mapping)
        """
        ...

    @abstractmethod
    async def get_db_map_for_prefix(
        self, *, prefix: str, db_name: str | None = None
    ) -> dict[str, list[str]]:
        """Get a dict containing a list of collections for each database, or a specific
        database (if `db_name` is provided).

        Only returns databases that start with the given prefix, and it returns the
        database names with `prefix` stripped. An empty dict is returned if `prefix` is
        empty. If `db_name` is provided but no collections exist, an empty list is
        returned with the database name as the key.
        """
        ...
