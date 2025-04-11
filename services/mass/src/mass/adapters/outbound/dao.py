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
#

"""Contains the ResourceDaoCollection, which houses a DAO for each resource class"""

from hexkit.protocols.dao import DaoFactoryProtocol
from pymongo import TEXT, MongoClient

from mass.config import Config
from mass.core import models
from mass.ports.outbound.dao import DaoCollectionPort, ResourceDao


class DaoNotFoundError(RuntimeError):
    """Raised when a DAO is not found."""

    def __init__(self, class_name: str):
        super().__init__(f"Could not find DAO for class '{class_name}'.")


class DaoCollection(DaoCollectionPort):
    """Provides a DAO for each configured searchable resource class"""

    @classmethod
    async def construct(
        cls,
        *,
        dao_factory: DaoFactoryProtocol,
        config: Config,
    ):
        """Initialize the DAO collection with one DAO for each resource class"""
        resource_daos: dict[str, ResourceDao] = {}
        for name in config.searchable_classes:
            resource_daos[name] = await dao_factory.get_dao(
                name=name, dto_model=models.Resource, id_field="id_"
            )

        return cls(config=config, resource_daos=resource_daos)

    def __init__(
        self,
        config: Config,
        resource_daos: dict[str, ResourceDao],
    ):
        """Initialize the collection of DAOs"""
        self._config = config
        self._resource_daos = resource_daos
        self._indexes_created = False

    def get_dao(self, *, class_name: str) -> ResourceDao:
        """Returns a dao for the given resource class name

        Raises:
            DaoNotFoundError: if the DAO isn't found
        """
        try:
            return self._resource_daos[class_name]
        except KeyError as err:
            raise DaoNotFoundError(class_name=class_name) from err

    def create_collections_and_indexes_if_needed(self) -> None:
        """Create collections and indexes if this hasn't been done yet."""
        if self._indexes_created:
            return

        # get client
        client: MongoClient = MongoClient(
            str(self._config.mongo_dsn.get_secret_value())
        )
        db = client[self._config.db_name]

        existing_collections = set(db.list_collection_names())

        # loop through configured classes (i.e. the expected collection names)
        for expected_collection_name in self._config.searchable_classes:
            if expected_collection_name not in existing_collections:
                db.create_collection(expected_collection_name)
            collection = db[expected_collection_name]

            # see if the wildcard text index exists and add it if not
            wildcard_text_index_exists = any(
                index["name"] == f"$**_{TEXT}" for index in collection.list_indexes()
            )

            if not wildcard_text_index_exists:
                collection.create_index([("$**", TEXT)])

        # close client and remember that the indexes have been set up
        client.close()
        self._indexes_created = True

    def recreate_collections_and_indexes(self) -> None:
        """Recreate collections and indexes if they have been removed."""
        self._indexes_created = False
        self.create_collections_and_indexes_if_needed()
