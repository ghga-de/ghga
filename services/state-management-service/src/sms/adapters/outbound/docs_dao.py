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
"""Contains the implementation of the DocsDao, providing the state management for MongoDB"""

from motor.motor_asyncio import AsyncIOMotorClient

from sms.config import Config
from sms.models import Criteria, DocumentType
from sms.ports.outbound.docs_dao import DocsDaoPort

DEFAULT_DBS: tuple[str, str, str] = ("admin", "config", "local")


class DocsDao(DocsDaoPort):
    """A class to perform CRUD operations in MongoDB."""

    def __init__(self, *, config: Config):
        """Initialize a DocDao instance. Do not call this directly, instead use context
        manager.
        """
        self._config = config

    async def __aenter__(self):
        """Enter the context manager."""
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(
            self._config.db_connection_str.get_secret_value()
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit the context manager and close the client connection."""
        if self._client:
            self._client.close()

    async def get(
        self, *, db_name: str, collection: str, criteria: Criteria
    ) -> list[DocumentType]:
        """Get documents satisfying the criteria.

        Args:
        - `db_name`: The database name.
        - `collection`: The collection name.
        - `criteria`: The criteria to use for filtering the documents (mapping)
        """
        return [x async for x in self._client[db_name][collection].find(criteria)]

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
        collection_instance = self._client[db_name][collection]

        for doc in documents:
            await collection_instance.update_one(
                {id_field: doc[id_field]}, {"$set": doc}, upsert=True
            )

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
        await self._client[db_name][collection].delete_many(criteria)

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
        if db_name:
            full_db_name = f"{prefix}{db_name}"
            return {
                db_name: sorted(
                    await self._client[full_db_name].list_collection_names()
                )
            }

        return {
            db.removeprefix(prefix): sorted(
                await self._client[db].list_collection_names()
            )
            for db in await self._client.list_database_names()
            if db.startswith(prefix) and db not in DEFAULT_DBS
        }
