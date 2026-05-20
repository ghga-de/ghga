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

"""Tests for the v3 migration"""

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from dcs.constants import DCS_PERSISTED_EVENTS_COLLECTION, DRS_OBJECTS_COLLECTION
from dcs.migrations import run_db_migrations
from tests_dcs.fixtures.config import get_config
from tests_dcs.migrations.v3_test_data import (
    EXPECTED_MIGRATED_DRS_OBJECTS,
    EXPECTED_MIGRATED_PERSISTED_EVENTS,
    OLD_DRS_OBJECTS,
    OLD_PERSISTED_EVENTS,
)

pytestmark = pytest.mark.asyncio()


async def test_v3_migration(mongodb: MongoDbFixture):
    """Test that the v3 migration correctly transforms events"""
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]

    drs_objects_collection = db[DRS_OBJECTS_COLLECTION]
    events_collection = db[DCS_PERSISTED_EVENTS_COLLECTION]

    # Clear collections
    events_collection.delete_many({})
    drs_objects_collection.delete_many({})

    # Run the migration to get the DB version to 2 first
    await run_db_migrations(config=config, target_version=2)

    # Now insert the test data
    drs_objects_collection.insert_many(OLD_DRS_OBJECTS)
    events_collection.insert_many(OLD_PERSISTED_EVENTS)

    await run_db_migrations(config=config, target_version=3)

    # Verify drs objects collection was migrated properly
    migrated_drs_objects = sorted(
        drs_objects_collection.find().to_list(), key=lambda m: m["_id"]
    )
    assert len(migrated_drs_objects) == len(EXPECTED_MIGRATED_DRS_OBJECTS)
    assert migrated_drs_objects == EXPECTED_MIGRATED_DRS_OBJECTS

    # Verify that the persisted events were migrated
    migrated_events = sorted(
        events_collection.find({}).to_list(), key=lambda d: d["_id"]
    )
    assert len(migrated_events) == len(EXPECTED_MIGRATED_PERSISTED_EVENTS)
    assert migrated_events == EXPECTED_MIGRATED_PERSISTED_EVENTS


async def test_with_already_migrated_data(mongodb: MongoDbFixture):
    """Test running the migration when the data has already been migrated"""
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]

    drs_objects_collection = db[DRS_OBJECTS_COLLECTION]
    events_collection = db[DCS_PERSISTED_EVENTS_COLLECTION]

    # Clear collections
    events_collection.delete_many({})
    drs_objects_collection.delete_many({})

    # Run the migration to get the DB version to 2 first
    await run_db_migrations(config=config, target_version=2)

    # Now insert the test data, using the already migrated data
    drs_objects_collection.insert_many(EXPECTED_MIGRATED_DRS_OBJECTS)
    events_collection.insert_many(EXPECTED_MIGRATED_PERSISTED_EVENTS)

    await run_db_migrations(config=config, target_version=3)

    # Verify drs objects collection docs look like they should
    migrated_drs_objects = sorted(
        drs_objects_collection.find().to_list(), key=lambda m: m["_id"]
    )
    assert len(migrated_drs_objects) == len(EXPECTED_MIGRATED_DRS_OBJECTS)
    assert migrated_drs_objects == EXPECTED_MIGRATED_DRS_OBJECTS

    # Verify that the persisted events look like they should
    migrated_events = sorted(
        events_collection.find({}).to_list(), key=lambda d: d["_id"]
    )
    assert len(migrated_events) == len(EXPECTED_MIGRATED_PERSISTED_EVENTS)
    assert migrated_events == EXPECTED_MIGRATED_PERSISTED_EVENTS
