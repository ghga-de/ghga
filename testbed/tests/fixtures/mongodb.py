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

from typing import Generator

from hexkit.providers.mongodb.provider import MongoDbDaoFactory
from hexkit.providers.mongodb.testutils import MongoDbFixture
from pydantic import SecretStr
from pymongo import MongoClient
from pymongo.errors import ExecutionTimeout, OperationFailure
from pytest import fixture

from src.config import Config

__all__ = ["mongodb_fixture"]


def drop_mongo_collections(db_connection_str: SecretStr, db_name: str):
    """Drop all mongodb collections in given database"""

    # Initialize new MongoDB connection
    client = MongoClient(str(db_connection_str.get_secret_value()))  # type: MongoClient

    try:
        # Access the target database
        db = client[db_name]

        collection_names = db.list_collection_names()
        for collection_name in collection_names:
            db.drop_collection(collection_name)

    except (ExecutionTimeout, OperationFailure) as error:
        print(
            f"An error occurred while dropping collections of mongo db {db_name}: {str(error)}"
        )

    finally:
        # Close the MongoDB client
        client.close()


@fixture
def mongodb_fixture(config: Config) -> Generator[MongoDbFixture, None, None]:
    """Pytest fixture for tests depending on the MongoDbDaoFactory DAO."""

    dao_factory = MongoDbDaoFactory(config=config)
    yield MongoDbFixture(config=config, dao_factory=dao_factory)

    # Drop all mongodb collections in service databases
    for db_name in config.service_db_names:
        drop_mongo_collections(
            db_connection_str=config.db_connection_str, db_name=db_name
        )
