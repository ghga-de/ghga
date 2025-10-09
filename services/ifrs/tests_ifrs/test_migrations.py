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

"""Tests for migration logic"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec

from ifrs.migrations import run_db_migrations
from tests_ifrs.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


async def test_v2_migration(mongodb: MongoDbFixture):
    """Test the v2 migration, which should update the persistent event collection
    so the fields use actual UUID and datetime field types.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]
    events_collection = db["ifrsPersistedEvents"]
    metadata_collection = db["file_metadata"]

    # affected fields - share value for fields of same type to simplify test
    date = datetime(2025, 4, 9, 15, 10, 2, 284123, tzinfo=UTC)
    migrated_date = date.replace(microsecond=284000)
    reverted_date = migrated_date.isoformat()
    old_uuid = "794fa7ab-fa80-493b-a08d-a6be41a07cde"
    migrated_uuid = UUID(old_uuid)

    # Prepare the old, migrated, and reverted data ahead of time
    # Start with the payloads for the persisted events: 1 affected and 1 unaffected
    unaffected_payload = {"file_id": "some-other-file"}
    affected_payload = {
        "s3_endpoint_alias": "test-alias",
        "file_id": "examplefile001",
        "object_id": old_uuid,
        "bucket_id": "bucket1",
        "decrypted_sha256": "",
        "decrypted_size": 1000,
        "decryption_secret_id": str(uuid4()),
        "content_offset": 128,
        "encrypted_size": 1128,
        "encrypted_part_size": 16,
        "encrypted_parts_md5": "abc123",
        "encrypted_parts_sha256": "abc123456",
        "upload_date": date.isoformat(),
    }
    migrated_affected_payload = affected_payload.copy()
    migrated_affected_payload["object_id"] = migrated_uuid
    migrated_affected_payload["upload_date"] = migrated_date

    reverted_affected_payload = affected_payload.copy()
    reverted_affected_payload["upload_date"] = reverted_date

    payloads: list[dict[str, Any]] = [affected_payload, unaffected_payload]
    migrated_payloads: list[dict[str, Any]] = [
        migrated_affected_payload,
        unaffected_payload,
    ]
    reverted_payloads: list[dict[str, Any]] = [
        reverted_affected_payload,
        unaffected_payload,
    ]

    old_events: list[dict[str, Any]] = []
    expected_migrated_events: list[dict[str, Any]] = []
    expected_reverted_events: list[dict[str, Any]] = []

    for i in range(2):
        old_event = {
            "_id": f"test-topic:key{i}",
            "topic": "test-topic",
            "payload": payloads[i],
            "key": f"key{i}",
            "type_": "some-type",
            "headers": {},
            "correlation_id": old_uuid,
            "created": date.isoformat(),
            "published": True,
        }

        migrated_event = old_event.copy()
        migrated_event.update(
            {
                "correlation_id": migrated_uuid,
                "created": migrated_date,
                "payload": migrated_payloads[i],
            }
        )
        reverted_event = old_event.copy()
        reverted_event.update(
            {"created": reverted_date, "payload": reverted_payloads[i]}
        )

        old_events.append(old_event)
        expected_migrated_events.append(migrated_event)
        expected_reverted_events.append(reverted_event)

    # Now set up the same trio of data for the other collection (file_metadata)
    old_metadata: list[dict[str, Any]] = []
    expected_migrated_metadata: list[dict[str, Any]] = []
    expected_reverted_metadata: list[dict[str, Any]] = []
    for i in range(3):
        old_file_metadata = {
            "_id": f"examplefile00{i}",
            "upload_date": date.isoformat(),
            "decryption_secret_id": "some-secret-id",
            "decrypted_size": 64 * 1024**2,
            "encrypted_part_size": 64 * 1024**2,
            "content_offset": 64 * 1024**2,
            "decrypted_sha256": "abc12345",
            "encrypted_parts_md5": ["1", "z", "4"],
            "encrypted_parts_sha256": ["a", "b", "c"],
            "storage_alias": "my-cool-storage",
            "object_id": old_uuid,
            "object_size": 64 * 1024**2 + 1234567,
        }
        migrated_file_metadata = old_file_metadata.copy()
        migrated_file_metadata.update(
            {"upload_date": migrated_date, "object_id": migrated_uuid}
        )
        reverted_file_metadata = old_file_metadata.copy()
        reverted_file_metadata.update({"upload_date": reverted_date})

        old_metadata.append(old_file_metadata)
        expected_migrated_metadata.append(migrated_file_metadata)
        expected_reverted_metadata.append(reverted_file_metadata)

    # Clear DB and insert test data for both collections
    events_collection.delete_many({})
    metadata_collection.delete_many({})
    events_collection.insert_many(old_events)
    metadata_collection.insert_many(old_metadata)

    # Run the migration targeting version 2
    await run_db_migrations(config=config, target_version=2)

    # Compare migrated EVENT docs against expected docs
    migrated_events = sorted(
        events_collection.find({}).to_list(), key=lambda d: d["_id"]
    )

    # Verify event_id is there and that it is a UUID, removing it in the process
    assert all(isinstance(doc.pop("event_id"), UUID) for doc in migrated_events)
    assert migrated_events == expected_migrated_events  # without event_id, should match

    # Compare migrated FILE METADATA docs against expected docs
    migrated_metadata = sorted(
        metadata_collection.find({}).to_list(), key=lambda d: d["_id"]
    )
    assert migrated_metadata == expected_migrated_metadata

    # Run reverse migration targeting version 1
    await run_db_migrations(config=config, target_version=1)

    # Compare reversal with expected data
    reverted_events = sorted(
        events_collection.find({}).to_list(), key=lambda d: d["_id"]
    )
    assert reverted_events == expected_reverted_events

    reverted_metadata = sorted(
        metadata_collection.find({}).to_list(), key=lambda d: d["_id"]
    )
    assert reverted_metadata == expected_reverted_metadata


async def test_migration_v2_on_migrated_file_metadata(mongodb: MongoDbFixture):
    """This test verifies that the fix for V2 will gracefully handle the presence of
    already migrated data by simply skipping it.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]
    metadata_collection = db["file_metadata"]

    # Create already migrated data (with UUID and datetime types)
    migrated_date = datetime(2025, 4, 9, 15, 10, 2, 284000, tzinfo=UTC)
    migrated_uuid = uuid4()

    data = {
        "_id": "test-file-id",
        "upload_date": migrated_date,
        "decryption_secret_id": "some-secret-id",
        "decrypted_size": 64 * 1024**2,
        "encrypted_part_size": 64 * 1024**2,
        "content_offset": 64 * 1024**2,
        "decrypted_sha256": "abc12345",
        "encrypted_parts_md5": ["1", "z", "4"],
        "encrypted_parts_sha256": ["a", "b", "c"],
        "storage_alias": "my-cool-storage",
        "object_id": migrated_uuid,
        "object_size": 64 * 1024**2 + 1234567,
    }

    # Clear out anything so we definitely start with an empty collection
    metadata_collection.delete_many({})

    # Insert the already migrated test data
    metadata_collection.insert_one(data)

    # Run the migration -- if no error then all good
    await run_db_migrations(config=config, target_version=2)


async def test_migration_v2_on_migrated_persisted_events(mongodb: MongoDbFixture):
    """This test verifies that the fix for V2 will gracefully handle the presence of
    already migrated persistent event data by simply skipping it.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]
    events_collection = db["ifrsPersistedEvents"]

    # Create already migrated event data (with UUID and datetime types)
    event = {
        "_id": "test-topic:test-key",
        "topic": "test-topic",
        "payload": {"upload_date": now_utc_ms_prec(), "object_id": uuid4()},
        "key": "test-key",
        "type_": "some-type",
        "headers": {},
        "correlation_id": uuid4(),
        "created": now_utc_ms_prec(),
        "published": True,
        "event_id": uuid4(),
    }

    # Clear out anything so we definitely start with an empty collection
    events_collection.delete_many({})

    # Insert already migrated item
    events_collection.insert_one(event)

    # Run the migration -- no news is good news
    await run_db_migrations(config=config, target_version=2)
