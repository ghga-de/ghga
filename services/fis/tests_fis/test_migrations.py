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
"""Verify the functionality of the migrations module."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from ghga_event_schemas.pydantic_ import FileUploadValidationSuccess
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec

from fis.main import DB_VERSION
from fis.migrations import run_db_migrations
from tests_fis.fixtures.config import get_config
from tests_fis.fixtures.joint import TEST_PAYLOAD

pytestmark = pytest.mark.asyncio()

TEST_CORRELATION_ID = "9b2af78e-2f36-49da-ab78-f0142d433038"


def make_test_event(file_id: str) -> FileUploadValidationSuccess:
    """Make a copy of the test event with the given file_id."""
    event = FileUploadValidationSuccess(
        upload_date=now_utc_ms_prec(),
        file_id=file_id,
        object_id=TEST_PAYLOAD.object_id,
        bucket_id=TEST_PAYLOAD.bucket_id,
        s3_endpoint_alias=TEST_PAYLOAD.storage_alias,
        decrypted_size=TEST_PAYLOAD.unencrypted_size,
        decryption_secret_id="",
        content_offset=0,
        encrypted_part_size=TEST_PAYLOAD.part_size,
        encrypted_parts_md5=TEST_PAYLOAD.encrypted_md5_checksums,
        encrypted_parts_sha256=TEST_PAYLOAD.encrypted_sha256_checksums,
        decrypted_sha256=TEST_PAYLOAD.unencrypted_checksum,
    )
    return event


@pytest.mark.skipif(DB_VERSION != 2, reason="Don't run tests for old migrations")
async def test_v2_migration(mongodb: MongoDbFixture):
    """Test the v2 migration, which should move existing outbox events to
    the new persisted events collection.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]

    # Make test data (outbox events)
    events = [make_test_event(file_id=f"event{i}") for i in range(3)]
    outbox_name = config.file_validations_collection
    outbox_collection = db[outbox_name]
    for event in events:
        outbox_collection.insert_one(
            {
                **event.model_dump(exclude={"file_id"}),
                "_id": event.file_id,
                "__metadata__": {
                    "published": False,
                    "deleted": False,
                    "correlation_id": TEST_CORRELATION_ID,
                },
            }
        )

    # Run the migration
    await run_db_migrations(config=config, target_version=2)

    # Verify that the events were moved to the new collection and the old collection dropped
    persisted_collection = db["fisPersistedEvents"]
    docs = persisted_collection.find().to_list()
    assert len(docs) == 3
    for doc in docs:
        assert doc["topic"] == config.file_interrogations_topic
        assert doc["type_"] == config.interrogation_success_type
        assert doc["key"] in [event.file_id for event in events]
        assert doc["correlation_id"] == TEST_CORRELATION_ID
        assert not doc["published"]
        assert doc["_id"] == f"{config.file_interrogations_topic}:{doc['key']}"
        assert doc["payload"]["file_id"] == doc["key"]

        index = int(doc["key"][-1])
        assert doc["payload"] == events[index].model_dump()
    assert outbox_name not in db.list_collection_names()


@pytest.mark.skipif(DB_VERSION != 3, reason="Don't run tests for old migrations")
async def test_v3_migration(mongodb: MongoDbFixture):
    """Test the v3 migration, which should update the persistent event collection
    so the fields use actual UUID and datetime field types.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]
    collection = db["fisPersistedEvents"]

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
        # Form the payloads within the persisted events separately, then hydrate
        old_payload = {
            "bucket_id": "staging",
            "content_offset": 0,
            "decrypted_sha256": "def",
            "decrypted_size": 52428800,
            "decryption_secret_id": "",
            "encrypted_part_size": 16777216,
            "encrypted_parts_md5": ["a", "b", "c"],
            "encrypted_parts_sha256": ["a", "b", "c"],
            "file_id": f"test_id{i}",
            "object_id": old_uuid,
            "s3_endpoint_alias": "staging",
            "upload_date": date.isoformat(),
        }

        migrated_payload = old_payload.copy()
        migrated_payload.update(
            {"object_id": migrated_uuid, "upload_date": migrated_date}
        )
        reverted_payload = old_payload.copy()
        reverted_payload.update({"upload_date": reverted_date})

        # Now form the top-level document data and inject the payloads
        old_event = {
            "_id": f"test-topic:key{i}",
            "topic": "test-topic",
            "payload": old_payload,
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
                "payload": migrated_payload,
                "correlation_id": migrated_uuid,
                "created": migrated_date,
            }
        )
        reverted_event = old_event.copy()
        reverted_event.update({"payload": reverted_payload, "created": reverted_date})

        old_events.append(old_event)
        expected_migrated_events.append(migrated_event)
        expected_reverted_events.append(reverted_event)

    # Clear DB and insert test data
    collection.delete_many({})
    collection.insert_many(old_events)

    # Run the migration
    await run_db_migrations(config=config, target_version=3)

    # Compare migrated data against expected migrated data
    migrated_events = sorted(collection.find({}).to_list(), key=lambda d: d["_id"])

    # Verify event_id is there and that it is a UUID, removing it in the process
    assert all(isinstance(doc.pop("event_id"), UUID) for doc in migrated_events)
    assert migrated_events == expected_migrated_events  # without event_id, should match

    # Run reverse migration
    await run_db_migrations(config=config, target_version=2)

    # Compare reversal with expected data
    reverted_events = sorted(collection.find({}).to_list(), key=lambda d: d["_id"])
    assert reverted_events == expected_reverted_events
