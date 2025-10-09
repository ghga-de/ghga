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

"""Tests for DCS database migrations"""

from asyncio import sleep
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.mongokafka.provider.persistent_pub import PersistentKafkaEvent
from hexkit.utils import now_utc_ms_prec

from dcs.core.models import AccessTimeDrsObject
from dcs.migrations import run_db_migrations
from tests_dcs.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


async def test_migration_v2_drs_objects(mongodb: MongoDbFixture):
    """Test the migration to DB version 2 and reversion to DB version 1.

    This test is only for the DRS objects, which are the main domain object.
    """
    config = get_config(sources=[mongodb.config])

    # Generate sample 'old' data that needs to be migrated
    data: list[dict[str, Any]] = []

    for i in range(3):
        old_drs_object = AccessTimeDrsObject(
            file_id=f"GHGAFile{i}",
            decryption_secret_id="abc123",
            decrypted_sha256="some-stuff",
            decrypted_size=100,
            encrypted_size=128,
            creation_date=now_as_utc(),
            s3_endpoint_alias="HD01",
            object_id=uuid4(),
            last_accessed=now_as_utc(),
        ).model_dump()

        # Convert data to the old format
        old_drs_object["_id"] = old_drs_object.pop("file_id")
        old_drs_object["object_id"] = str(old_drs_object["object_id"])
        old_drs_object["creation_date"] = old_drs_object["creation_date"].isoformat()
        old_drs_object["last_accessed"] = old_drs_object["last_accessed"].isoformat()
        data.append(old_drs_object)
        await sleep(0.1)  # sleep so timestamps are meaningfully different

    # Clear out anything so we definitely start with an empty collection
    db = mongodb.client[config.db_name]
    collection = db["drs_objects"]
    collection.delete_many({})

    # Insert the test data
    collection.insert_many(data)

    # Run the migration
    await run_db_migrations(config=config, target_version=2)

    # Retrieve the migrated data and compare
    migrated_data = collection.find().to_list()
    migrated_data.sort(key=lambda x: x["_id"])

    assert len(migrated_data) == len(data)
    for old, new in zip(data, migrated_data, strict=True):
        assert new["_id"] == old["_id"]

        new_creation = new["creation_date"]
        new_accessed = new["last_accessed"]

        # Make sure the migrated data has the right types
        assert isinstance(new["object_id"], UUID)
        assert isinstance(new_creation, datetime)
        assert isinstance(new_accessed, datetime)

        # Make sure the actual ID of the object ID field still matches the old one
        assert str(new["object_id"]) == old["object_id"]

        # rather than calculating exact date mig results (tested in hexkit), just verify
        #  that it's within half a millisecond
        max_time_diff = timedelta(microseconds=500)
        assert (
            abs(new_creation - datetime.fromisoformat(old["creation_date"]))
            < max_time_diff
        )
        assert (
            abs(new_accessed - datetime.fromisoformat(old["last_accessed"]))
            < max_time_diff
        )

        assert new_creation.microsecond % 1000 == 0
        assert new_accessed.microsecond % 1000 == 0

    # now unapply (dates will not have microseconds of course)
    await run_db_migrations(config=config, target_version=1)
    reverted_data = collection.find().to_list()
    reverted_data.sort(key=lambda x: x["_id"])
    assert len(reverted_data) == len(data)
    for reverted, new in zip(reverted_data, migrated_data, strict=True):
        assert isinstance(reverted["object_id"], str)
        assert isinstance(reverted["creation_date"], str)
        assert isinstance(reverted["last_accessed"], str)

        assert reverted["_id"] == str(new["_id"])
        assert reverted["creation_date"] == new["creation_date"].isoformat()
        assert reverted["last_accessed"] == new["last_accessed"].isoformat()


async def test_migration_v2_on_migrated_data(mongodb: MongoDbFixture):
    """This test is to verify that the fix for V2 will gracefully handle already
    migrated drs object data.
    """
    config = get_config(sources=[mongodb.config])

    data = AccessTimeDrsObject(
        file_id="test-file-id",
        decryption_secret_id="abc123",
        decrypted_sha256="some-stuff",
        decrypted_size=100,
        encrypted_size=128,
        creation_date=now_as_utc(),
        s3_endpoint_alias="HD01",
        object_id=uuid4(),
        last_accessed=now_as_utc(),
    ).model_dump()

    data["_id"] = data.pop("file_id")

    # Clear out anything so we definitely start with an empty collection
    db = mongodb.client[config.db_name]
    collection = db["drs_objects"]
    collection.delete_many({})

    # Insert the test data
    collection.insert_one(data)

    # Run the migration -- if no error then all good
    await run_db_migrations(config=config, target_version=2)


async def test_migration_v2_on_migrated_persisted_events_(mongodb: MongoDbFixture):
    """This test is to verify that the fix for V2 will gracefully handle already
    migrated persisted event data.
    """
    config = get_config(sources=[mongodb.config])

    file_registered_topic = config.file_registered_for_download_topic
    event = PersistentKafkaEvent(
        compaction_key="file_registered",
        topic=file_registered_topic,
        payload={"upload_date": now_utc_ms_prec()},
        correlation_id=uuid4(),
        key="something",
        type_="something",
        created=now_utc_ms_prec(),
        published=True,
    ).model_dump()
    event["_id"] = event.pop("compaction_key")

    # Clear out anything so we definitely start with an empty collection
    db = mongodb.client[config.db_name]
    collection = db["dcsPersistedEvents"]
    collection.delete_many({})

    # Insert already migrated item
    collection.insert_one(event)

    # Run the migration -- no news is good news
    await run_db_migrations(config=config, target_version=2)


async def test_migration_v2_persisted_events(mongodb: MongoDbFixture):
    """Test the migration to DB version 2 and reversion to DB version 1.

    This test is only for persisted events.
    """
    config = get_config(sources=[mongodb.config])

    download_served_topic = config.download_served_topic
    file_registered_topic = config.file_registered_for_download_topic
    file_deleted_topic = config.file_deleted_topic

    new_object_id = uuid4()
    new_upload_date = now_as_utc()

    # Make one test event for each of the three stored topics
    old_events: list[dict[str, Any]] = []
    topics = [download_served_topic, file_registered_topic, file_deleted_topic]
    for i, topic in enumerate(topics):
        await sleep(0.1)
        reverted_payload = {}
        if topic == download_served_topic:
            reverted_payload = {"object_id": str(new_object_id)}
        elif topic == file_registered_topic:
            reverted_payload = {"upload_date": new_upload_date.isoformat()}
        event = {
            "_id": f"{topic}:key{i}",
            "topic": topic,
            "payload": reverted_payload,
            "key": f"key{i}",
            "type_": "some-type",
            "headers": {},
            "correlation_id": str(uuid4()),
            "created": now_as_utc().isoformat(),
            "published": True,
        }
        old_events.append(event)

    # Clear out anything so we definitely start with an empty collection
    db = mongodb.client[config.db_name]
    collection = db["dcsPersistedEvents"]
    collection.delete_many({})

    # Insert the test data
    collection.insert_many(old_events)

    # Run the migration
    await run_db_migrations(config=config, target_version=2)

    # Retrieve the migrated data and compare
    migrated_events = collection.find().to_list()
    migrated_events.sort(key=lambda x: x["_id"])

    assert len(migrated_events) == 3
    # Compare old and new data
    max_time_diff = timedelta(microseconds=500)
    for migrated, old in zip(migrated_events, old_events, strict=True):
        assert isinstance(migrated["created"], datetime)
        assert isinstance(migrated["correlation_id"], UUID)
        assert (
            abs(migrated["created"] - datetime.fromisoformat(old["created"]))
            < max_time_diff
        )
        assert str(migrated["correlation_id"]) == old["correlation_id"]

        # check the migrated payload fields and make sure the types/content are right
        migrated_payload = migrated["payload"]
        if migrated_object_id := migrated_payload.get("object_id"):
            assert isinstance(migrated_object_id, UUID)
            assert str(migrated_object_id) == old["payload"]["object_id"]
        if migrated_upload_date := migrated_payload.get("upload_date"):
            assert isinstance(migrated_upload_date, datetime)
            assert (
                abs(
                    migrated_upload_date
                    - datetime.fromisoformat(old["payload"]["upload_date"])
                )
                < max_time_diff
            )

    # Now reverse the migration and verify that part:
    await run_db_migrations(config=config, target_version=1)
    reverted_events = collection.find().to_list()
    reverted_events.sort(key=lambda x: x["_id"])

    for reverted, migrated in zip(reverted_events, migrated_events, strict=True):
        assert isinstance(reverted["created"], str)
        assert isinstance(reverted["correlation_id"], str)
        assert reverted["created"] == migrated["created"].isoformat()
        assert reverted["correlation_id"] == str(migrated["correlation_id"])

        # check the payload fields
        reverted_payload = reverted["payload"]
        if reverted_object_id := reverted_payload.get("object_id"):
            assert isinstance(reverted_object_id, str)
            assert reverted_object_id == str(migrated["payload"]["object_id"])
        if reverted_upload_date := reverted_payload.get("upload_date"):
            assert isinstance(reverted_upload_date, str)
            assert (
                reverted_upload_date == migrated["payload"]["upload_date"].isoformat()
            )
