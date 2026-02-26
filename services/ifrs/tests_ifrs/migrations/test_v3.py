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

"""Tests for V3 migration logic"""

from uuid import uuid4

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec
from tests_ifrs.fixtures.config import get_config

from ifrs.migrations import run_db_migrations
from ifrs.migrations.definitions.v3 import derive_file_id_from_accession

pytestmark = pytest.mark.asyncio


async def test_v3_migration(mongodb: MongoDbFixture):
    """Test the v3 migration which renames and reorganizes fields in file_metadata
    and ifrsPersistedEvents collections for the Sarcastic Fringehead epic.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]
    events_collection = db["ifrsPersistedEvents"]
    metadata_collection = db["file_metadata"]

    # Create test data for the FileMetadata objects
    old_metadata = [
        {
            "_id": f"GHGA00{i}",
            "upload_date": now_utc_ms_prec(),
            "storage_alias": "test-storage",
            "bucket_id": "test-bucket",
            "object_id": uuid4(),
            "decryption_secret_id": f"secret-{i}",
            "content_offset": 0,
            "decrypted_size": 64 * 1024**2,
            "object_size": 64 * 1024**2 + 1000,
            "decrypted_sha256": "decrypted-checksum",
            "encrypted_parts_md5": ["md5-1", "md5-2"],
            "encrypted_parts_sha256": ["sha-1", "sha-2"],
            "encrypted_part_size": 16 * 1024**2,
        }
        for i in range(3)
    ]

    expected_migrated_metadata = []
    for old_doc in old_metadata:
        migrated = {
            "_id": derive_file_id_from_accession(old_doc["_id"]),
            "archive_date": old_doc["upload_date"],
            "storage_alias": old_doc["storage_alias"],
            "bucket_id": old_doc["bucket_id"],
            "object_id": old_doc["object_id"],
            "secret_id": old_doc["decryption_secret_id"],
            "decrypted_size": old_doc["decrypted_size"],
            "encrypted_size": old_doc["object_size"],
            "decrypted_sha256": old_doc["decrypted_sha256"],
            "encrypted_parts_md5": old_doc["encrypted_parts_md5"],
            "encrypted_parts_sha256": old_doc["encrypted_parts_sha256"],
            "part_size": old_doc["encrypted_part_size"],
        }
        expected_migrated_metadata.append(migrated)

    # Create persisted event data for the FileInternallyRegistered events
    file_registered_payload = {
        "file_id": "GHGA001",
        "object_id": uuid4(),
        "upload_date": now_utc_ms_prec(),
        "s3_endpoint_alias": "HD01",
        "decryption_secret_id": "test-secret-id",
        "encrypted_part_size": 16 * 1024**2,
        "content_offset": 128,
        "bucket_id": "test-bucket",
        "decrypted_size": 64 * 1024**2,
        "encrypted_size": 64 * 1024**2 + 1000,
        "decrypted_sha256": "checksum",
        "encrypted_parts_md5": ["md5"],
        "encrypted_parts_sha256": ["sha"],
    }

    file_deleted_payload = {"file_id": "GHGA007"}

    old_events = [
        {
            "_id": "test-topic:GHGA001",
            "topic": "topic1",
            "payload": file_registered_payload,
            "key": "GHGA001",
            "type_": "file_internally_registered",
            "headers": {},
            "correlation_id": uuid4(),
            "created": now_utc_ms_prec(),
            "published": True,
            "event_id": uuid4(),
        },
        {
            "_id": "test-topic:GHGA007",
            "topic": "topic2",
            "payload": file_deleted_payload,
            "key": "GHGA007",
            "type_": "file_deleted",
            "headers": {},
            "correlation_id": uuid4(),
            "created": now_utc_ms_prec(),
            "published": True,
            "event_id": uuid4(),
        },
    ]

    ghga001_uuid = derive_file_id_from_accession("GHGA001")
    migrated_registration_payload = {
        "file_id": ghga001_uuid,
        "archive_date": file_registered_payload["upload_date"],
        "storage_alias": "HD01",
        "bucket_id": "test-bucket",
        "object_id": file_registered_payload["object_id"],
        "secret_id": "test-secret-id",
        "part_size": 16 * 1024**2,
        "decrypted_size": 64 * 1024**2,
        "encrypted_size": 64 * 1024**2 + 1000,
        "decrypted_sha256": "checksum",
        "encrypted_parts_md5": ["md5"],
        "encrypted_parts_sha256": ["sha"],
    }

    ghga007_uuid = derive_file_id_from_accession("GHGA007")
    migrated_file_deleted_payload = {"file_id": ghga007_uuid}
    expected_migrated_events = [
        {
            "_id": f"test-topic:{ghga001_uuid}",
            "topic": "topic1",
            "payload": migrated_registration_payload,
            "key": str(ghga001_uuid),
            "type_": "file_internally_registered",
            "headers": {},
            "correlation_id": old_events[0]["correlation_id"],
            "created": old_events[0]["created"],
            "published": False,
            "event_id": old_events[0]["event_id"],
        },
        {
            "_id": f"test-topic:{ghga007_uuid}",
            "topic": "topic2",
            "payload": migrated_file_deleted_payload,
            "key": str(ghga007_uuid),
            "type_": "file_deleted",
            "headers": {},
            "correlation_id": old_events[1]["correlation_id"],
            "created": old_events[1]["created"],
            "published": False,
            "event_id": old_events[1]["event_id"],
        },
    ]

    # Clear collections and insert old data
    events_collection.delete_many({})
    metadata_collection.delete_many({})
    events_collection.insert_many(old_events)
    metadata_collection.insert_many(old_metadata)

    # Run the migration (at last)
    await run_db_migrations(config=config, target_version=3)

    # Verify file metadata was migrated properly
    migrated_metadata = sorted(
        metadata_collection.find().to_list(), key=lambda m: m["secret_id"]
    )
    assert len(migrated_metadata) == len(expected_migrated_metadata)
    assert migrated_metadata == expected_migrated_metadata

    # Verify that the events were migrated
    migrated_events = sorted(
        events_collection.find({}).to_list(), key=lambda d: d["topic"]
    )
    assert len(migrated_events) == 2
    assert migrated_events == expected_migrated_events


async def test_v3_migration_on_already_migrated_file_metadata(mongodb: MongoDbFixture):
    """Verify that V3 migration gracefully handles already migrated file_metadata
    by skipping it (checking for presence of 'archive_date' field).
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]
    metadata_collection = db["file_metadata"]

    metadata_collection.delete_many({})

    # Get DB state to version 2 before running migration
    await run_db_migrations(config=config, target_version=2)
    migrated_data = {
        "_id": uuid4(),
        "archive_date": now_utc_ms_prec(),
        "secret_id": "test-secret",
        "part_size": 16 * 1024**2,
        "encrypted_size": 64 * 1024**2 + 1000,
        "decrypted_size": 64 * 1024**2,
        "encrypted_parts_md5": ["md5"],
        "encrypted_parts_sha256": ["sha"],
        "decrypted_sha256": "checksum",
        "storage_alias": "test-storage",
        "bucket_id": "test-bucket",
        "object_id": uuid4(),
    }

    metadata_collection.insert_one(migrated_data)
    await run_db_migrations(config=config, target_version=3)
    result = metadata_collection.find_one({"_id": migrated_data["_id"]})
    assert result == migrated_data


async def test_v3_migration_on_already_migrated_events(mongodb: MongoDbFixture):
    """Verify that V3 migration gracefully handles already migrated events
    by skipping them.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client[config.db_name]
    events_collection = db["ifrsPersistedEvents"]

    events_collection.delete_many({})
    await run_db_migrations(config=config, target_version=2)
    file_id = uuid4()
    migrated_event = {
        "_id": f"test-topic:{file_id}",
        "topic": "test-topic",
        "payload": {
            "file_id": file_id,
            "archive_date": now_utc_ms_prec(),
            "storage_alias": "HD01",
            "secret_id": "test-secret-id",
            "part_size": 16 * 1024**2,
            "bucket_id": "test-bucket",
            "decrypted_size": 64 * 1024**2,
            "encrypted_size": 64 * 1024**2 + 1000,
            "decrypted_sha256": "checksum",
            "encrypted_parts_md5": ["md5"],
            "encrypted_parts_sha256": ["sha"],
        },
        "key": str(file_id),
        "type_": "file_internally_registered",
        "headers": {},
        "correlation_id": uuid4(),
        "created": now_utc_ms_prec(),
        "published": False,
        "event_id": uuid4(),
    }

    events_collection.insert_one(migrated_event)
    await run_db_migrations(config=config, target_version=3)
    result = events_collection.find_one({"_id": migrated_event["_id"]})
    assert result == migrated_event
