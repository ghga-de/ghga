# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Tests for functionality related to the outbox subscriber."""

from typing import Callable
from unittest.mock import AsyncMock

import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.correlation import get_correlation_id
from hexkit.custom_types import JsonObject
from hexkit.providers.mongodb import MongoDbDaoFactory
from ifrs.adapters.inbound import models
from ifrs.adapters.inbound.utils import check_record_is_new, make_record_from_update
from ifrs.adapters.outbound.dao import (
    get_file_deletion_requested_dao,
)
from logot import Logot, logged
from pydantic import BaseModel

from tests_ifrs.fixtures.joint import JointFixture

CHANGE_EVENT_TYPE = "upserted"
DELETE_EVENT_TYPE = "deleted"


TEST_FILE_ID = "test_id"

TEST_NONSTAGED_FILE_REQUESTED = event_schemas.NonStagedFileRequested(
    file_id=TEST_FILE_ID,
    target_object_id="",
    target_bucket_id="",
    s3_endpoint_alias="",
    decrypted_sha256="",
)

TEST_FILE_UPLOAD_VALIDATION_SUCCESS = event_schemas.FileUploadValidationSuccess(
    upload_date=now_as_utc().isoformat(),
    file_id=TEST_FILE_ID,
    object_id="",
    bucket_id="",
    s3_endpoint_alias="",
    decrypted_size=0,
    decryption_secret_id="",
    content_offset=0,
    encrypted_part_size=0,
    encrypted_parts_md5=[],
    encrypted_parts_sha256=[],
    decrypted_sha256="",
)

TEST_FILE_DELETION_REQUESTED = event_schemas.FileDeletionRequested(file_id=TEST_FILE_ID)


def test_make_record_from_update():
    """Test the get_record function"""
    record = make_record_from_update(
        models.FileDeletionRequestedRecord, TEST_FILE_DELETION_REQUESTED
    )
    isinstance(record, models.FileDeletionRequestedRecord)
    assert record.model_dump() == {
        "correlation_id": get_correlation_id(),
        "file_id": TEST_FILE_ID,
    }


@pytest.mark.asyncio()
async def test_idempotence(joint_fixture: JointFixture, logot: Logot):
    """Test the idempotence functionality when encountering a record that already exists"""
    # First, insert the record that we want to collide with
    dao_factory = MongoDbDaoFactory(config=joint_fixture.config)
    dao = await get_file_deletion_requested_dao(dao_factory=dao_factory)
    record = models.FileDeletionRequestedRecord(
        correlation_id=get_correlation_id(), file_id=TEST_FILE_ID
    )

    record_is_new = await check_record_is_new(
        dao=dao,
        resource_id=TEST_FILE_ID,
        update=TEST_FILE_DELETION_REQUESTED,
        record=record,
    )

    assert record_is_new

    # insert record into the DB
    await dao.insert(record)

    # rerun the assertion and verify that the result is False and that we get a log
    record_is_new = await check_record_is_new(
        dao=dao,
        resource_id=TEST_FILE_ID,
        update=TEST_FILE_DELETION_REQUESTED,
        record=record,
    )

    assert not record_is_new

    # examine logs
    logot.assert_logged(
        logged.debug(
            "Event with 'FileDeletionRequested' schema for resource ID 'test_id' has"
            + " already been processed under current correlation_id. Skipping."
        )
    )


@pytest.mark.parametrize(
    "upsertion_event, topic_config_name, method_name",
    [
        (
            TEST_FILE_DELETION_REQUESTED.model_dump(),
            "files_to_delete_topic",
            "upsert_file_deletion_requested",
        ),
        (
            TEST_FILE_UPLOAD_VALIDATION_SUCCESS.model_dump(),
            "files_to_register_topic",
            "upsert_file_upload_validation_success",
        ),
        (
            TEST_NONSTAGED_FILE_REQUESTED.model_dump(),
            "files_to_stage_topic",
            "upsert_nonstaged_file_requested",
        ),
    ],
)
@pytest.mark.asyncio()
async def test_outbox_subscriber_routing(
    joint_fixture: JointFixture,
    upsertion_event: JsonObject,
    topic_config_name: str,
    method_name: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Make sure the outbox subscriber calls the correct method on the idempotence
    handler for the given event.
    """
    topic = getattr(joint_fixture.config, topic_config_name)
    mock = AsyncMock()
    monkeypatch.setattr(joint_fixture.idempotence_handler, method_name, mock)
    await joint_fixture.kafka.publish_event(
        payload=upsertion_event,
        type_=CHANGE_EVENT_TYPE,
        topic=topic,
        key=TEST_FILE_ID,
    )

    await joint_fixture.outbox_subscriber.run(forever=False)
    mock.assert_awaited_once()


@pytest.mark.parametrize(
    "deletion_event, topic_config_name, event_type",
    [
        (
            TEST_FILE_DELETION_REQUESTED.model_dump(),
            "files_to_delete_topic",
            "FileDeletionRequested",
        ),
        (
            TEST_FILE_UPLOAD_VALIDATION_SUCCESS.model_dump(),
            "files_to_register_topic",
            "FileUploadValidationSuccess",
        ),
        (
            TEST_NONSTAGED_FILE_REQUESTED.model_dump(),
            "files_to_stage_topic",
            "NonStagedFileRequested",
        ),
    ],
)
@pytest.mark.asyncio()
async def test_deletion_logs(
    joint_fixture: JointFixture,
    logot: Logot,
    deletion_event: JsonObject,
    topic_config_name: str,
    event_type: str,
):
    """Test that the outbox subscriber logs deletions correctly.
    Consume a 'DELETED' event type for each of the outbox events.
    """
    topic = getattr(joint_fixture.config, topic_config_name)
    await joint_fixture.kafka.publish_event(
        payload=deletion_event,
        type_=DELETE_EVENT_TYPE,
        topic=topic,
        key=TEST_FILE_ID,
    )
    await joint_fixture.outbox_subscriber.run(forever=False)
    logot.assert_logged(
        logged.warning(
            f"Received DELETED-type event for {event_type} with resource ID '%s'",
        )
    )


@pytest.mark.parametrize(
    "update, method_to_patch, event_schema_name",
    [
        (
            TEST_FILE_DELETION_REQUESTED,
            "delete_file",
            "FileDeletionRequested",
        ),
        (
            TEST_FILE_UPLOAD_VALIDATION_SUCCESS,
            "register_file",
            "FileUploadValidationSuccess",
        ),
        (
            TEST_NONSTAGED_FILE_REQUESTED,
            "stage_registered_file",
            "NonStagedFileRequested",
        ),
    ],
)
@pytest.mark.asyncio()
async def test_idempotence_handler(
    joint_fixture: JointFixture,
    logot: Logot,
    update: BaseModel,
    method_to_patch: str,
    event_schema_name: str,
):
    """Test that the IdempotenceHandler handles events correctly.

    This tests the methods inside the file registry that are called by the outbox.
    The registry methods are patched with a mock that can be inspected later for calls.
    The expected behavior is that the method is called once, and then not called again,
    because the record is already in the database.
    """
    mock = AsyncMock()

    setattr(joint_fixture.file_registry, method_to_patch, mock)

    method_map: dict[str, Callable] = {
        "FileDeletionRequested": joint_fixture.idempotence_handler.upsert_file_deletion_requested,
        "FileUploadValidationSuccess": joint_fixture.idempotence_handler.upsert_file_upload_validation_success,
        "NonStagedFileRequested": joint_fixture.idempotence_handler.upsert_nonstaged_file_requested,
    }

    # Set which 'upsert_xyz' method to call on the idempotence handler
    method_to_call = method_map[event_schema_name]

    # call idempotence handler method once, which should call the file registry method
    await method_to_call(resource_id=TEST_FILE_ID, update=update)

    mock.assert_awaited_once()
    mock.reset_mock()

    # call the method once more, which should emit a debug log and not hit the registry
    await method_to_call(resource_id=TEST_FILE_ID, update=update)

    mock.assert_not_awaited()

    logot.assert_logged(
        logged.debug(
            f"Event with '{event_schema_name}' schema for resource ID '{TEST_FILE_ID}'"
            + " has already been processed under current correlation_id. Skipping."
        )
    )
