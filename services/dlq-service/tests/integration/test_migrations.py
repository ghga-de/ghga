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

"""Tests for DLQS DB migrations."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from dlqs.migrations import run_db_migrations
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


async def test_v2_migration(mongodb: MongoDbFixture):
    """Test the forward and reverse migration for v2"""
    config = get_config(sources=[mongodb.config])

    db = mongodb.client[config.db_name]
    collection = db["dlqEvents"]

    timestamp = datetime(2025, 6, 1, 17, 4, 8, 484738, tzinfo=UTC)
    timestamp_migrated = timestamp.replace(microsecond=485000)
    cid = str(uuid4())

    event: dict[str, Any] = {
        "_id": None,
        "timestamp": timestamp.isoformat(),
        "headers": {"correlation_id": cid},
        "topic": "my-topic",
        "type_": "my_type",
        "payload": {
            "some_field": "some_value",
        },
        "key": "abc123",
        "dlq_info": {
            "service": "old-service",
            "partition": 0,
            "offset": 400,
            "exc_class": "ConnectionAttemptError",
            "exc_msg": "Attempt to connect to the SMTP server failed.",
        },
    }

    expected_migrated_events: list[dict[str, Any]] = []
    expected_reverted_events: list[dict[str, Any]] = []
    collection.delete_many({})
    for _ in range(3):
        old_event = deepcopy(event)
        old_event["_id"] = str(uuid4())
        collection.insert_one(old_event)

        # prepare migrated event
        migrated_event = deepcopy(event)
        del migrated_event["dlq_info"]["partition"]
        del migrated_event["dlq_info"]["offset"]
        migrated_event["_id"] = UUID(old_event["_id"])
        migrated_event["dlq_info"]["original_event_id"] = None
        migrated_event["timestamp"] = timestamp_migrated
        expected_migrated_events.append(migrated_event)

        reverted_event = old_event.copy()  # don't need deepcopy this time
        reverted_event["timestamp"] = timestamp_migrated.isoformat()
        reverted_event["dlq_info"]["partition"] = 0
        reverted_event["dlq_info"]["offset"] = 0
        expected_reverted_events.append(reverted_event)

    # Sort everything
    expected_migrated_events.sort(key=lambda x: str(x.get("_id")))
    expected_reverted_events.sort(key=lambda x: x["_id"])

    await run_db_migrations(config=config, target_version=2)

    # Retrieve migrated data and evaluate
    migrated_events = collection.find({}).to_list()
    migrated_events.sort(key=lambda x: str(x.get("_id")))

    assert len(migrated_events) == 3
    assert migrated_events == expected_migrated_events

    # # Run the reverse migration
    await run_db_migrations(config=config, target_version=1)

    # Retrieve the reverted data
    reverted_events = collection.find({}).sort("_id").to_list()
    assert reverted_events == expected_reverted_events
