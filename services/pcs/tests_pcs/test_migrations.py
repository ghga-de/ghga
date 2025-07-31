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

"""Test for migration logic."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from pcs.migrations import run_db_migrations
from tests_pcs.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


async def test_v2_migration(mongodb: MongoDbFixture):
    """Test the v2 migration, which should update the persistent event collection
    so the fields use actual UUID and datetime field types.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]
    collection = db["pcsPersistedEvents"]

    # affected fields - share value for fields of same type to simplify test
    date = datetime(2025, 4, 9, 15, 10, 2, 284123, tzinfo=UTC)
    migrated_date = date.replace(microsecond=284000)
    reverted_date = migrated_date.isoformat()

    old_uuid = "794fa7ab-fa80-493b-a08d-a6be41a07cde"
    migrated_uuid = UUID(old_uuid)

    # Prepare the old, migrated, and reverted data ahead of time
    old_events: list[dict[str, Any]] = []
    expected_migrated_events: list[dict[str, Any]] = []
    expected_reverted_events: list[dict[str, Any]] = []

    for i in range(1, 3):
        old_event = {
            "_id": f"test-topic:key{i}",
            "topic": "test-topic",
            "payload": {"file_id": "the-best-file-id"},
            "key": f"key{i}",
            "type_": "some-type",
            "headers": {},
            "correlation_id": old_uuid,
            "created": date.isoformat(),
            "published": True,
        }

        migrated_event = old_event.copy()
        migrated_event.update(
            {"correlation_id": migrated_uuid, "created": migrated_date}
        )
        reverted_event = old_event.copy()
        reverted_event.update({"created": reverted_date})

        old_events.append(old_event)
        expected_migrated_events.append(migrated_event)
        expected_reverted_events.append(reverted_event)

    # Clear DB and insert test data
    collection.delete_many({})
    collection.insert_many(old_events)

    # Run the migration
    await run_db_migrations(config=config, target_version=2)

    # Compare migrated data against expected migrated data
    migrated_events = sorted(collection.find({}).to_list(), key=lambda d: d["_id"])

    # Verify event_id is there and that it is a UUID, removing it in the process
    assert all(isinstance(doc.pop("event_id"), UUID) for doc in migrated_events)
    assert migrated_events == expected_migrated_events  # without event_id, should match

    # Run reverse migration
    await run_db_migrations(config=config, target_version=1)

    # Compare reversal with expected data
    reverted_events = sorted(collection.find({}).to_list(), key=lambda d: d["_id"])
    assert reverted_events == expected_reverted_events
