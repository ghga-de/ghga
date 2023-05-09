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
import glob
import re
from typing import AsyncGenerator

import pytest_asyncio
from hexkit.providers.mongodb.testutils import (
    MongoDbDaoFactory,
    MongoDbFixture,
    config_from_mongodb_container,
)
from pymongo import TEXT
from testcontainers.mongodb import MongoDbContainer

from tests.fixtures.utils import get_resources_from_file


@pytest_asyncio.fixture
async def populated_mongodb_fixture() -> AsyncGenerator[MongoDbFixture, None]:
    """Pytest fixture for a pre-populated mongodb fixture"""

    with MongoDbContainer(image="mongo:6.0.3") as mongodb:
        config = config_from_mongodb_container(mongodb)
        dao_factory = MongoDbDaoFactory(config=config)
        client = mongodb.get_connection_client()

        # Populate a collection for each file in test_data
        filename_pattern = re.compile(r"\/(\w+)\.json")
        for filename in glob.glob("tests/fixtures/test_data/*.json"):
            match_obj = re.search(filename_pattern, filename)
            if match_obj:
                collection_name = match_obj.groups()[0]
                resources = get_resources_from_file(filename)
                client[config.db_name][collection_name].insert_many(resources)
                client[config.db_name][collection_name].create_index(
                    keys=[("$**", TEXT)]
                )

        yield MongoDbFixture(config=config, dao_factory=dao_factory)
