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
"""Contains port definition for a Doc Handler"""

from abc import ABC, abstractmethod

from sms.models import Criteria, DocumentType


class DocsDaoPort(ABC):
    """Port definition for a Doc Handler"""

    @abstractmethod
    async def get(
        self, *, db_name: str, collection: str, criteria: Criteria
    ) -> list[DocumentType]:
        """Get documents satisfying the criteria.

        Args:
        - `db_name`: The database name.
        - `collection`: The collection name.
        - `criteria`: The criteria to use for filtering the documents (mapping)
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

        Args:
        - `db_name`: The database name.
        - `collection`: The collection name.
        - `criteria`: The criteria to use for filtering the documents (mapping)
        """
        ...
