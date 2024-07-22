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
"""Contains the abstract definition of a DocsHandler."""

from abc import ABC, abstractmethod

from sms.models import Criteria, DocumentType, UpsertionDetails


class DocsHandlerPort(ABC):
    """Port definition for a Doc Handler"""

    class MissingIdFieldError(RuntimeError):
        """Raised when the id field is missing."""

        def __init__(self, *, id_field: str):
            super().__init__(f"The id '{id_field}' field is missing on a document.")

    class OperationError(RuntimeError):
        """Raised when a database operation fails."""

    class ReadOperationError(OperationError):
        """Raised when a read (get) operation fails."""

        def __init__(self, *, criteria: Criteria):
            super().__init__(f"The DB read failed. Criteria used: {criteria}.")

    class UpsertionError(OperationError):
        """Raised when an upsert operation fails."""

        def __init__(self, *, id_field: str):
            super().__init__(f"The DB upsertion failed. id_field used: '{id_field}'.")

    class DeletionError(OperationError):
        """Raised when a deletion operation fails."""

        def __init__(self, *, criteria: Criteria):
            super().__init__(f"The DB deletion failed. Criteria used: {criteria}.")

    class CriteriaFormatError(RuntimeError):
        """Raised when the criteria format is invalid."""

        def __init__(self, *, key: str):
            super().__init__(f"The value for key '{key}' is invalid.")

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...
