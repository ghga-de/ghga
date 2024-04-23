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
#

"""Shared fixtures"""

import pytest
from hexkit.providers.akafka.testutils import get_kafka_fixture
from hexkit.providers.mongodb.testutils import MongoDbFixture, get_mongodb_fixture

from wps.config import Config

from .fixtures.datasets import DATASET

kafka_fixture = get_kafka_fixture("session")
mongodb_fixture = get_mongodb_fixture("session")


@pytest.fixture(name="empty_mongodb")
def empty_mongodb_fixture(mongodb_fixture: MongoDbFixture) -> MongoDbFixture:
    """MongoDB Fixture with empty database."""
    mongodb_fixture.empty_collections()
    return mongodb_fixture


@pytest.fixture(name="populated_mongodb")
def populated_mongodb_fixture(
    empty_mongodb: MongoDbFixture, config: Config
) -> MongoDbFixture:
    """MongoDB Fixture with a database populated with one dataset."""
    database = empty_mongodb.client.get_database(config.db_name)
    collection = database.get_collection(config.datasets_collection)
    dataset = DATASET.model_dump()
    dataset["_id"] = dataset.pop("id")
    collection.insert_one(dataset)
    return empty_mongodb
