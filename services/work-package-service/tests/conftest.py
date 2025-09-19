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

"""Shared fixtures"""

from uuid import UUID

import pytest
from hexkit.providers.akafka.testutils import (  # noqa: F401
    kafka_container_fixture,
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    MongoDbFixture,
    mongodb_container_fixture,
    mongodb_fixture,
)

from tests.fixtures import FILE_BOX_ID, RDU_BOX_ID
from wps.config import Config

from .fixtures.datasets import DATASET


@pytest.fixture(name="mongodb_populated")
def mongodb_populated_fixture(
    mongodb: MongoDbFixture, config: Config
) -> MongoDbFixture:
    """MongoDB Fixture with a database populated with one dataset and one upload box."""
    database = mongodb.client.get_database(config.db_name)

    # Insert a dataset into the database
    dataset_collection = database.get_collection(config.datasets_collection)
    dataset = DATASET.model_dump()
    dataset["_id"] = dataset.pop("id")
    dataset_collection.insert_one(dataset)

    # Insert an upload box into the database
    upload_box = {
        "_id": UUID(RDU_BOX_ID),
        "file_upload_box_id": UUID(FILE_BOX_ID),
        "title": "Test Upload Box",
        "description": "Box for testing expired access",
    }
    box_collection = database[config.upload_boxes_collection]
    box_collection.insert_one(upload_box)
    return mongodb
