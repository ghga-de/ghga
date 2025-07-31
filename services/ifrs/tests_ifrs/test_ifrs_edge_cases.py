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

"""Tests edge cases not covered by the typical journey test."""

import logging
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.custom_types import JsonObject
from hexkit.providers.s3.testutils import (
    FileObject,
    S3Fixture,  # noqa: F401
    temp_file_object,
    tmp_file,  # noqa: F401
)
from hexkit.utils import now_utc_ms_prec

from ifrs.ports.inbound.file_registry import FileRegistryPort
from tests_ifrs.fixtures.example_data import EXAMPLE_METADATA, EXAMPLE_METADATA_BASE
from tests_ifrs.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()

TEST_FILE_ID = "test_id"
TEST_NONSTAGED_FILE_REQUESTED = event_schemas.NonStagedFileRequested(
    file_id=TEST_FILE_ID,
    target_object_id=uuid4(),
    target_bucket_id="",
    s3_endpoint_alias="",
    decrypted_sha256="",
)

TEST_FILE_UPLOAD_VALIDATION_SUCCESS = event_schemas.FileUploadValidationSuccess(
    upload_date=now_utc_ms_prec(),
    file_id=TEST_FILE_ID,
    object_id=uuid4(),
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


async def test_register_with_empty_staging(joint_fixture: JointFixture):
    """Test registration of a file when the file content is missing from staging."""
    with pytest.raises(FileRegistryPort.FileContentNotInStagingError):
        await joint_fixture.file_registry.register_file(
            file_without_object_id=EXAMPLE_METADATA_BASE,
            staging_object_id=uuid4(),
            staging_bucket_id=joint_fixture.staging_bucket,
        )


async def test_reregistration(
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa F811
):
    """Test the re-registration of a file with identical metadata (should not result in
    an exception). Test PR/Push workflow message
    """
    storage = joint_fixture.s3
    storage_alias = joint_fixture.storage_aliases.node1

    # place example content in the staging bucket:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": joint_fixture.staging_bucket,
            "object_id": str(EXAMPLE_METADATA.object_id),
        }
    )
    await storage.populate_file_objects(file_objects=[file_object])

    # register new file from the staging bucket:
    # (And check if an event informing about the new registration has been published.)
    file_metadata_base = EXAMPLE_METADATA_BASE.model_copy(
        update={"storage_alias": storage_alias}
    )

    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_internally_registered_topic
    ) as recorder:
        await joint_fixture.file_registry.register_file(
            file_without_object_id=file_metadata_base,
            staging_object_id=EXAMPLE_METADATA.object_id,
            staging_bucket_id=joint_fixture.staging_bucket,
        )

    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.payload["object_id"] != ""
    assert event.type_ == joint_fixture.config.file_internally_registered_type

    # re-register the same file from the staging bucket:
    # (A second event is not expected.)
    async with joint_fixture.kafka.expect_events(
        events=[],
        in_topic=joint_fixture.config.file_internally_registered_topic,
    ):
        await joint_fixture.file_registry.register_file(
            file_without_object_id=file_metadata_base,
            staging_object_id=EXAMPLE_METADATA.object_id,
            staging_bucket_id=joint_fixture.staging_bucket,
        )


async def test_reregistration_with_updated_metadata(
    caplog,
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa: F811
):
    """Check that a re-registration of a file with updated metadata fails with the
    expected exception.
    """
    storage = joint_fixture.s3
    storage_alias = joint_fixture.storage_aliases.node1
    # place example content in the staging bucket:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": joint_fixture.staging_bucket,
            "object_id": str(EXAMPLE_METADATA.object_id),
        }
    )
    await storage.populate_file_objects(file_objects=[file_object])

    # register new file from the staging bucket:
    # (And check if an event informing about the new registration has been published.)
    file_metadata_base = EXAMPLE_METADATA_BASE.model_copy(
        update={"storage_alias": storage_alias}
    )

    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_internally_registered_topic,
    ) as recorder:
        await joint_fixture.file_registry.register_file(
            file_without_object_id=file_metadata_base,
            staging_object_id=EXAMPLE_METADATA.object_id,
            staging_bucket_id=joint_fixture.staging_bucket,
        )

    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.payload["object_id"] != ""
    assert event.type_ == joint_fixture.config.file_internally_registered_type

    # try to re-register the same file with updated metadata:
    # Check for correct logging
    file_update = file_metadata_base.model_copy(update={"decrypted_size": 4321})

    caplog.clear()

    with caplog.at_level(level=logging.WARNING, logger="ifrs.core.file_registry"):
        expected_message = str(
            FileRegistryPort.FileUpdateError(file_id=file_metadata_base.file_id)
        )
        await joint_fixture.file_registry.register_file(
            file_without_object_id=file_update,
            staging_object_id=EXAMPLE_METADATA.object_id,
            staging_bucket_id=joint_fixture.staging_bucket,
        )
        assert len(caplog.messages) == 1
        assert expected_message in caplog.messages


async def test_stage_non_existing_file(joint_fixture: JointFixture, caplog):
    """Check that requesting to stage a non-registered file fails with the expected
    exception.
    """
    file_id = "notregisteredfile001"
    error = joint_fixture.file_registry.FileNotInRegistryError(file_id=file_id)

    caplog.clear()
    await joint_fixture.file_registry.stage_registered_file(
        file_id=file_id,
        decrypted_sha256=EXAMPLE_METADATA_BASE.decrypted_sha256,
        outbox_object_id=EXAMPLE_METADATA.object_id,
        outbox_bucket_id=joint_fixture.outbox_bucket,
    )
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.message == str(error)
    assert record.levelname == "ERROR"


async def test_stage_checksum_mismatch(
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa: F811
):
    """Check that requesting to stage a registered file to the outbox by specifying the
    wrong checksum fails with the expected exception.
    """
    # populate the database with a corresponding file metadata entry:
    await joint_fixture.file_metadata_dao.insert(EXAMPLE_METADATA)

    storage = joint_fixture.s3
    storage_alias = joint_fixture.storage_aliases.node1

    bucket_id = joint_fixture.config.object_storages[storage_alias].bucket
    # place the content for an example file in the permanent storage:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": bucket_id,
            "object_id": str(EXAMPLE_METADATA.object_id),
        }
    )
    await storage.populate_file_objects(file_objects=[file_object])

    # request a stage for the registered file to the outbox by specifying a wrong checksum:
    with pytest.raises(FileRegistryPort.ChecksumMismatchError):
        await joint_fixture.file_registry.stage_registered_file(
            file_id=EXAMPLE_METADATA_BASE.file_id,
            decrypted_sha256=(
                "e6da6d6d05cc057964877aad8a3e9ad712c8abeae279dfa2f89b07eba7ef8abe"
            ),
            outbox_object_id=EXAMPLE_METADATA.object_id,
            outbox_bucket_id=joint_fixture.outbox_bucket,
        )


async def test_storage_db_inconsistency(joint_fixture: JointFixture):
    """Check that an inconsistency between the database and the storage, whereby the
    database contains a file metadata registration but the storage is missing the
    corresponding content, results in the expected exception.
    """
    # populate the database with metadata on an example file even though the storage is
    # empty:
    await joint_fixture.file_metadata_dao.insert(EXAMPLE_METADATA)

    # request a stage for the registered file by specifying a wrong checksum:
    with pytest.raises(FileRegistryPort.FileInRegistryButNotInStorageError):
        await joint_fixture.file_registry.stage_registered_file(
            file_id=EXAMPLE_METADATA_BASE.file_id,
            decrypted_sha256=EXAMPLE_METADATA_BASE.decrypted_sha256,
            outbox_object_id=EXAMPLE_METADATA.object_id,
            outbox_bucket_id=joint_fixture.outbox_bucket,
        )


@pytest.mark.parametrize(
    "event, topic_config_name, type_config_name, method_name",
    [
        (
            TEST_FILE_DELETION_REQUESTED.model_dump(),
            "file_deletion_request_topic",
            "file_deletion_request_type",
            "delete_file",
        ),
        (
            TEST_FILE_UPLOAD_VALIDATION_SUCCESS.model_dump(),
            "file_interrogations_topic",
            "interrogation_success_type",
            "register_file",
        ),
        (
            TEST_NONSTAGED_FILE_REQUESTED.model_dump(),
            "files_to_stage_topic",
            "files_to_stage_type",
            "stage_registered_file",
        ),
    ],
)
async def test_event_subscriber_routing(
    joint_fixture: JointFixture,
    event: JsonObject,
    topic_config_name: str,
    type_config_name: str,
    method_name: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Make sure the event subscriber calls the correct method on the file registry."""
    topic = getattr(joint_fixture.config, topic_config_name)
    type_ = getattr(joint_fixture.config, type_config_name)
    mock = AsyncMock()
    monkeypatch.setattr(joint_fixture.file_registry, method_name, mock)
    await joint_fixture.kafka.publish_event(
        payload=event,
        type_=type_,
        topic=topic,
        key=TEST_FILE_ID,
    )

    await joint_fixture.event_subscriber.run(forever=False)
    mock.assert_awaited_once()


async def test_error_during_copy(joint_fixture: JointFixture, caplog):
    """Errors during `object_storage.copy_object` should be logged and re-raised."""
    # Insert FileMetadata record into the DB
    dao = joint_fixture.file_metadata_dao
    await dao.insert(EXAMPLE_METADATA)

    s3_alias = EXAMPLE_METADATA.storage_alias
    source_bucket = joint_fixture.config.object_storages[s3_alias].bucket
    outbox_bucket = "outbox-bucket"

    # Upload a matching object to S3
    with temp_file_object(source_bucket, str(EXAMPLE_METADATA.object_id)) as file:
        await joint_fixture.s3.populate_file_objects([file])

    # Run the file-staging operation to encounter an error (outbox bucket doesn't exist)
    caplog.clear()
    caplog.set_level("CRITICAL")
    with pytest.raises(joint_fixture.file_registry.CopyOperationError):
        await joint_fixture.file_registry.stage_registered_file(
            file_id=EXAMPLE_METADATA.file_id,
            decrypted_sha256=EXAMPLE_METADATA.decrypted_sha256,
            outbox_bucket_id=outbox_bucket,
            outbox_object_id=EXAMPLE_METADATA.object_id,
        )

    # Verify the log message exists
    assert caplog.records
    assert caplog.records[0].message == (
        "Fatal error occurred while copying file with the ID 'examplefile001'"
        + " to the bucket 'outbox-bucket'. The exception is: The bucket"
        + " with ID 'outbox-bucket' does not exist."
    )

    # Upload the file to the outbox bucket so we trigger ObjectAlreadyExistsError
    with temp_file_object(outbox_bucket, str(EXAMPLE_METADATA.object_id)) as file:
        await joint_fixture.s3.populate_file_objects([file])

    # Run the file-staging operation to encounter the error
    caplog.clear()
    caplog.set_level("INFO")
    await joint_fixture.file_registry.stage_registered_file(
        file_id=EXAMPLE_METADATA.file_id,
        decrypted_sha256=EXAMPLE_METADATA.decrypted_sha256,
        outbox_bucket_id=outbox_bucket,
        outbox_object_id=EXAMPLE_METADATA.object_id,
    )

    assert caplog.records
    assert caplog.records[0].getMessage() == (
        "Object corresponding to file ID 'examplefile001' is already in the outbox."
    )


async def test_copy_when_file_exists_in_outbox(joint_fixture: JointFixture, caplog):
    """Test that `FileRegistry.stage_registered_file` returns early if a copy is
    unnecessary.
    """
    # Insert FileMetadata record into the DB
    dao = joint_fixture.file_metadata_dao
    await dao.insert(EXAMPLE_METADATA)

    # Populate the source and dest buckets
    s3_alias = EXAMPLE_METADATA.storage_alias
    source_bucket = joint_fixture.config.object_storages[s3_alias].bucket
    outbox_bucket = "outbox-bucket"
    with temp_file_object(source_bucket, str(EXAMPLE_METADATA.object_id)) as file:
        await joint_fixture.s3.populate_file_objects([file])

    with temp_file_object(outbox_bucket, str(EXAMPLE_METADATA.object_id)) as file:
        await joint_fixture.s3.populate_file_objects([file])

    # Run the file-staging operation, which should return early (it will catch the
    # error raised by the hexkit provider, which asserts that the file doesn't exist
    # in the outbox)
    caplog.clear()
    caplog.set_level("INFO")
    await joint_fixture.file_registry.stage_registered_file(
        file_id=EXAMPLE_METADATA.file_id,
        decrypted_sha256=EXAMPLE_METADATA.decrypted_sha256,
        outbox_bucket_id=outbox_bucket,
        outbox_object_id=EXAMPLE_METADATA.object_id,
    )

    # Check the log
    assert caplog.records
    assert caplog.records[0].getMessage() == (
        "Object corresponding to file ID 'examplefile001' is already in the outbox."
    )
