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

import pytest
from ghga_event_schemas.pydantic_ import FileUploadValidationSuccess
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.mongodb.testutils import MongoDbFixture

from fis.migrations import run_db_migrations
from tests_fis.fixtures.config import get_config
from tests_fis.fixtures.joint import TEST_PAYLOAD

pytestmark = pytest.mark.asyncio()

TEST_CORRELATION_ID = "9b2af78e-2f36-49da-ab78-f0142d433038"


def make_test_event(file_id: str) -> FileUploadValidationSuccess:
    """Make a copy of the test event with the given file_id."""
    event = FileUploadValidationSuccess(
        upload_date=now_as_utc().isoformat(),
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
