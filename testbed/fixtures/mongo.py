# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Fixture for testing code that uses the MongoDbDaoFactory provider."""

from time import sleep
from typing import Any, Generator, Mapping, Optional, Union

from hexkit.providers.mongodb.provider import MongoDbDaoFactory
from hexkit.providers.mongodb.testutils import MongoDbFixture
from pymongo import MongoClient
from pymongo.errors import ExecutionTimeout, OperationFailure
from pytest import fixture

from fixtures.config import Config

__all__ = [
    "mongo_fixture",
    "MongoClient",
    "MongoDbFixture",
]


class MongoFixture:
    """An augmented Mongo DB fixture containing a MongoClient"""

    config: Config
    client: MongoClient
    dao_factory: MongoDbDaoFactory

    def __init__(
        self, config: Config, client: MongoClient, dao_factory: MongoDbDaoFactory
    ):
        self.config = config
        self.client = client
        self.dao_factory = dao_factory

    def empty_databases(
        self,
        db_names: Optional[Union[str, list[str]]] = None,
        exclude_collections: Optional[Union[str, list[str]]] = None,
    ):
        """Drop all mongodb collections in the given database(s).

        You can also specify collection(s) that should be excluded
        from the operation, i.e. collections that should be kept.
        """
        if db_names is None:
            db_names = self.config.service_db_names
        elif isinstance(db_names, str):
            db_names = [db_names]
        if exclude_collections is None:
            exclude_collections = []
        if isinstance(exclude_collections, str):
            exclude_collections = [exclude_collections]
        excluded_collections = set(exclude_collections)
        for db_name in db_names:
            try:
                db = self.client[db_name]
                collection_names = db.list_collection_names()
                for collection_name in collection_names:
                    if collection_name not in excluded_collections:
                        db.drop_collection(collection_name)
            except (ExecutionTimeout, OperationFailure) as error:
                raise RuntimeError(
                    f"Could not drop collection(s) of Mongo database {db_name}"
                ) from error

    def find_document(
        self, db_name: str, collection_name: str, mapping: Mapping[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Return one document from the given collection matching the given filter."""
        db = self.client[db_name]
        collection = db.get_collection(collection_name)
        return collection.find_one(mapping)

    def wait_for_document(
        self,
        db_name: str,
        collection_name: str,
        mapping: Mapping[str, Any],
        timeout=10,
    ) -> Any:
        """Wait for one document from the given collection matching the given filter."""
        slept = 0.0
        interval = 0.1
        while slept < timeout:
            document = self.find_document(db_name, collection_name, mapping)
            if document is not None:
                return document
            sleep(interval)
            slept += interval
        return None

    def replace_document(
        self, db_name: str, collection_name: str, document: Mapping[str, Any]
    ):
        """Replace one document in the given collection."""
        db = self.client[db_name]
        collection = db.get_collection(collection_name)
        collection.replace_one({"_id": document["_id"]}, document, upsert=True)

    def remove_document(
        self, db_name: str, collection_name: str, document: Mapping[str, Any]
    ):
        """Remove one document in the given collection with the given document."""
        db = self.client[db_name]
        collection = db.get_collection(collection_name)
        collection.delete_many(document)


@fixture(name="mongo")
def mongo_fixture(config: Config) -> Generator[MongoFixture, None, None]:
    """Pytest fixture for tests depending on the Mongo database."""

    dao_factory = MongoDbDaoFactory(config=config)
    db_connection_str = str(config.db_connection_str.get_secret_value())
    client: MongoClient = MongoClient(db_connection_str)
    mongo_db = MongoDbFixture(config=config, dao_factory=dao_factory)
    mongo = MongoFixture(
        config=mongo_db.config,  # pyright: ignore
        client=client,
        dao_factory=mongo_db.dao_factory,
    )
    yield mongo
    client.close()
