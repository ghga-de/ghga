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
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from hexkit.custom_types import JsonObject
from hexkit.providers.s3.testutils import (
    FileObject,
    S3Fixture,  # noqa: F401
    tmp_file,  # noqa: F401
)
from hexkit.utils import now_utc_ms_prec

from ifrs.core.models import FileDeletionRequested, FileMetadata, NonStagedFileRequested
from ifrs.ports.inbound.file_registry import FileRegistryPort
from tests_ifrs.fixtures.example_data import (
    EXAMPLE_ARCHIVABLE_FILE,
    EXAMPLE_AWAITING_ARCHIVAL,
)
from tests_ifrs.fixtures.joint import JointFixture
from tests_ifrs.fixtures.utils import (
    DOWNLOAD_BUCKET,
    INTERROGATION_BUCKET,
    PERMANENT_BUCKET,
)

pytestmark = pytest.mark.asyncio

TEST_FILE_ID = UUID("a8470191-77b1-4e74-bf63-e5db3b39e84a")
TEST_NONSTAGED_FILE_REQUESTED = NonStagedFileRequested(
    file_id=TEST_FILE_ID,
    target_object_id=uuid4(),
    target_bucket_id=DOWNLOAD_BUCKET,
    storage_alias="HD01",
    decrypted_sha256="",
)


TEST_FILE_DELETION_REQUESTED = FileDeletionRequested(file_id=TEST_FILE_ID)


async def test_register_when_file_not_in_interrogation(joint_fixture: JointFixture):
    """Test registration of a file when the file content is missing from the
    interrogation bucket.
    """
    file = EXAMPLE_ARCHIVABLE_FILE.model_copy(update={"id": uuid4()})
    with pytest.raises(FileRegistryPort.FileNotInInterrogationError):
        await joint_fixture.file_registry.register_file(file=file)


async def test_registration_idempotence(
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa F811
):
    """Test the re-registration of a file that has already been registered."""
    # place example content in the interrogation bucket:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": INTERROGATION_BUCKET,
            "object_id": str(EXAMPLE_ARCHIVABLE_FILE.object_id),
        }
    )
    storage_alias = joint_fixture.storage_aliases.node0
    storage = joint_fixture.federated_s3.storages[storage_alias]
    await storage.populate_file_objects([file_object])

    # Get the size of the tmp_file and make the archivable file object
    archivable_file = EXAMPLE_ARCHIVABLE_FILE.model_copy(
        update={"storage_alias": storage_alias, "encrypted_size": len(tmp_file.content)}
    )

    # register new file from the interrogation bucket and check for event
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_internally_registered_topic
    ) as recorder:
        await joint_fixture.file_registry.register_file(file=archivable_file)

    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.payload["file_id"] == str(archivable_file.id)
    archive_date = datetime.fromisoformat(event.payload["archive_date"])
    assert (now_utc_ms_prec() - archive_date).seconds < 5
    assert event.type_ == joint_fixture.config.file_internally_registered_type

    # register the file again. Should not publish anything.
    async with joint_fixture.kafka.expect_events(
        events=[],
        in_topic=joint_fixture.config.file_internally_registered_topic,
    ):
        await joint_fixture.file_registry.register_file(file=archivable_file)


async def test_reregistration_with_updated_metadata(
    caplog,
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa: F811
):
    """Check that a re-registration of a file with different metadata fails with the
    expected exception.
    """
    # place example content in the interrogation bucket:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": INTERROGATION_BUCKET,
            "object_id": str(EXAMPLE_ARCHIVABLE_FILE.object_id),
        }
    )
    storage_alias = joint_fixture.storage_aliases.node0
    storage = joint_fixture.federated_s3.storages[storage_alias]
    await storage.populate_file_objects([file_object])

    # register new file from the interrogation bucket:
    # (And check if an event informing about the new registration has been published.)
    archivable_file = EXAMPLE_ARCHIVABLE_FILE.model_copy(
        update={"storage_alias": storage_alias, "encrypted_size": len(tmp_file.content)}
    )

    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_internally_registered_topic,
    ) as recorder:
        await joint_fixture.file_registry.register_file(file=archivable_file)

    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.payload["file_id"] == str(archivable_file.id)
    assert event.type_ == joint_fixture.config.file_internally_registered_type

    # try to re-register the same file with updated metadata:
    # Check for correct logging
    file_update = archivable_file.model_copy(update={"decrypted_size": 4321})

    caplog.clear()

    with caplog.at_level(level=logging.WARNING, logger="ifrs.core.file_registry"):
        expected_message = str(
            FileRegistryPort.FileUpdateError(file_id=archivable_file.id)
        )
        await joint_fixture.file_registry.register_file(file=file_update)
        assert len(caplog.messages) == 1
        assert expected_message in caplog.messages


async def test_stage_non_existing_file(joint_fixture: JointFixture, caplog):
    """Check that requesting to stage a non-registered file fails with the expected
    exception.
    """
    file_id = uuid4()
    error = joint_fixture.file_registry.FileNotInRegistryError(file_id=file_id)

    caplog.clear()
    await joint_fixture.file_registry.stage_registered_file(
        file_id=file_id,
        decrypted_sha256=EXAMPLE_ARCHIVABLE_FILE.decrypted_sha256,
        download_bucket_id=DOWNLOAD_BUCKET,
        download_object_id=EXAMPLE_ARCHIVABLE_FILE.id,
    )
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.message == str(error)
    assert record.levelname == "ERROR"


async def test_stage_checksum_mismatch(
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa: F811
):
    """Make sure the IFRS raises an error if a file download staging request contains
    the wrong decrypted SHA256 checksum.
    """
    # populate the database with a corresponding file metadata entry:
    file_metadata = FileMetadata(
        archive_date=now_utc_ms_prec(),
        encrypted_size=len(tmp_file.content),
        object_id=uuid4(),
        **EXAMPLE_ARCHIVABLE_FILE.model_dump(exclude={"encrypted_size", "object_id"}),
    )
    await joint_fixture.file_metadata_dao.insert(file_metadata)

    storage_alias = joint_fixture.storage_aliases.node0
    storage = joint_fixture.federated_s3.storages[storage_alias]
    bucket_id = joint_fixture.config.object_storages[storage_alias].bucket
    # place the content for an example file in the permanent storage:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": bucket_id,
            "object_id": str(file_metadata.object_id),
        }
    )
    await storage.populate_file_objects([file_object])

    # request the IFRS to stage a registered file to the download bucket, but
    #  specify the wrong checksum
    with pytest.raises(FileRegistryPort.ChecksumMismatchError):
        await joint_fixture.file_registry.stage_registered_file(
            file_id=file_metadata.id,
            decrypted_sha256=(
                "e6da6d6d05cc057964877aad8a3e9ad712c8abeae279dfa2f89b07eba7ef8abe"
            ),
            download_object_id=file_metadata.object_id,
            download_bucket_id=DOWNLOAD_BUCKET,
        )


async def test_storage_db_inconsistency(joint_fixture: JointFixture):
    """Check that an inconsistency between the database and the storage, whereby the
    database contains a file metadata registration but the storage is missing the
    corresponding content, results in the expected exception.
    """
    # populate the database with metadata on an example file that doesn't exist
    file_metadata = FileMetadata(
        archive_date=now_utc_ms_prec(),
        **EXAMPLE_ARCHIVABLE_FILE.model_dump(),
    )
    await joint_fixture.file_metadata_dao.insert(file_metadata)

    # request a stage for the registered file by specifying a wrong checksum:
    with pytest.raises(FileRegistryPort.FileInRegistryButNotInStorageError):
        await joint_fixture.file_registry.stage_registered_file(
            file_id=file_metadata.id,
            decrypted_sha256=file_metadata.decrypted_sha256,
            download_object_id=file_metadata.object_id,
            download_bucket_id=DOWNLOAD_BUCKET,
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
        key=str(TEST_FILE_ID),
    )

    await joint_fixture.event_subscriber.run(forever=False)
    mock.assert_awaited_once()


@pytest.mark.parametrize(
    "state",
    [
        "init",
        "inbox",
        "interrogated",
        "cancelled",
        "failed",
        "awaiting_archival",
        "archived",
    ],
)
async def test_handle_file_upload(
    joint_fixture: JointFixture, state: str, monkeypatch: pytest.MonkeyPatch
):
    """Test the behavior of the core's .handle_file_upload() method.

    The .register_file() method is only called when the state is "awaiting_archival".

    In other cases, the data should be ignored (with a log).
    """
    mock = AsyncMock()
    monkeypatch.setattr(joint_fixture.file_registry, "register_file", mock)

    # This example model will work for all states, even if it's not "realistic"
    event = EXAMPLE_AWAITING_ARCHIVAL.model_copy(update={"state": state})

    await joint_fixture.kafka.publish_event(
        payload=event.model_dump(mode="json"),
        type_="upserted",
        topic=joint_fixture.config.file_upload_topic,
        key=str(EXAMPLE_AWAITING_ARCHIVAL.id),
    )

    await joint_fixture.event_subscriber.run(forever=False)
    if state == "awaiting_archival":
        mock.assert_awaited()
    else:
        mock.assert_not_awaited()


async def test_error_during_copy_to_download_bucket(
    joint_fixture: JointFixture,
    caplog,
    tmp_file: FileObject,  # noqa: F811
):
    """Errors during `object_storage.copy_object` should be logged and re-raised."""
    # Insert FileMetadata record into the DB
    permanent_object_id = uuid4()
    file_metadata = FileMetadata(
        archive_date=now_utc_ms_prec(),
        encrypted_size=len(tmp_file.content),
        object_id=permanent_object_id,
        bucket_id=PERMANENT_BUCKET,
        **EXAMPLE_ARCHIVABLE_FILE.model_dump(
            exclude={"encrypted_size", "bucket_id", "object_id"}
        ),
    )
    await joint_fixture.file_metadata_dao.insert(file_metadata)

    # place example content in the permanent bucket:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": PERMANENT_BUCKET,
            "object_id": str(permanent_object_id),
        }
    )
    storage_alias = joint_fixture.storage_aliases.node0
    storage = joint_fixture.federated_s3.storages[storage_alias]
    await storage.populate_file_objects([file_object])

    # Run the file-staging operation to trigger an error (download bucket doesn't exist)
    caplog.clear()
    caplog.set_level("CRITICAL")
    with pytest.raises(joint_fixture.file_registry.CopyOperationError):
        await joint_fixture.file_registry.stage_registered_file(
            file_id=file_metadata.id,
            decrypted_sha256=file_metadata.decrypted_sha256,
            download_bucket_id="does-not-exist",
            download_object_id=uuid4(),
        )

    # Verify the log message is correct
    assert caplog.records
    assert caplog.records[0].message == (
        f"Fatal error occurred while copying file with the ID '{file_metadata.id}'"
        + " to the bucket 'does-not-exist'. The exception is: The bucket"
        + " with ID 'does-not-exist' does not exist."
    )

    # Upload the file to the download bucket so we trigger ObjectAlreadyExistsError
    download_object_id = uuid4()
    staged_object = file_object.model_copy(
        deep=True,
        update={"bucket_id": DOWNLOAD_BUCKET, "object_id": str(download_object_id)},
    )
    await storage.populate_file_objects([staged_object])

    # Run the file-staging operation to encounter the error
    caplog.clear()
    caplog.set_level("INFO")
    await joint_fixture.file_registry.stage_registered_file(
        file_id=file_metadata.id,
        decrypted_sha256=file_metadata.decrypted_sha256,
        download_bucket_id=DOWNLOAD_BUCKET,
        download_object_id=download_object_id,
    )

    assert caplog.records
    assert caplog.records[0].getMessage() == (
        f"File with ID '{file_metadata.id}' is already in the download bucket."
    )
