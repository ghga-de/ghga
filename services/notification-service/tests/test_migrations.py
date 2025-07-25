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

"""Tests for NS DB migrations."""

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from ns.migrations import run_db_migrations
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


async def test_migration_v2(mongodb: MongoDbFixture):
    """Test the migration to version 2."""
    config = get_config(sources=[mongodb.config])

    # Insert some test data using the fixture client
    collection = mongodb.client[config.db_name]["notification_records"]
    collection.insert_many(
        [
            {"_id": 1},
            {"_id": 2},
            {"_id": 3},
        ]
    )

    # Sanity check to verify that the documents exist before migration
    assert len(collection.find().to_list()) == 3

    # Run the migration, which should drop the `notification_records` collection
    await run_db_migrations(config=config, target_version=2)

    # Assert that the collection is dropped/empty (we don't actually care if
    #  it is removed from the database, just that it is empty)
    assert collection.find().to_list() == []
