# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Tests for the UploadController class"""

import logging
from asyncio import sleep
from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
import pytest_asyncio
from ghga_event_schemas.pydantic_ import (
    FileInternallyRegistered,
    FileUploadState,
    InterrogationSuccess,
)
from hexkit.protocols.dao import ResourceNotFoundError, UniqueConstraintViolationError
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.utils import now_utc_ms_prec

from tests_ucs.fixtures.joint import JointRig
from tests_ucs.fixtures.utils import (
    DECRYPTED_SIZE,
    ENCRYPTED_SIZE,
    PART_SIZE,
    TEST_MAX_BOX_SIZE,
    make_file_upload,
)
from ucs.constants import MAX_PART_COUNT, MAX_PART_SIZE, MIN_PART_SIZE
from ucs.core.models import FileUpload, UploadActivity
from ucs.ports.inbound.controller import UploadControllerPort

MIN_SLEEP = 0.001

pytestmark = pytest.mark.asyncio()


@pytest_asyncio.fixture(autouse=True)
async def create_default_bucket(rig: JointRig):
    """Create the `test-inbox` bucket automatically for tests."""
    await rig.object_storages.for_alias("test")[1].create_bucket("test-inbox")


async def test_create_new_box(rig: JointRig):
    """Test creating a new FileUploadBox"""
    box_id = await rig.create_default_box()
    assert rig.file_upload_box_dao.latest.id == box_id
    assert rig.file_upload_box_dao.latest.version == 0
    assert rig.file_upload_box_dao.latest.state == "open"


async def test_create_new_file_upload(rig: JointRig):
    """Test creating a new FileUpload"""
    # First create a FileUploadBox
    file_upload_dao = rig.file_upload_dao
    box_id = await rig.create_default_box()

    # Then create a FileUpload within the box
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Verify the FileUpload was created with S3 fields populated
    assert file_upload_dao.latest.id == file_id
    assert file_upload_dao.latest.alias == "test_file"
    assert file_upload_dao.latest.decrypted_sha256 is None
    assert file_upload_dao.latest.decrypted_size == DECRYPTED_SIZE
    assert file_upload_dao.latest.storage_alias == "test"
    assert now_utc_ms_prec() - file_upload_dao.latest.initiated < timedelta(seconds=5)
    assert not file_upload_dao.latest.completed


async def test_get_part_url(rig: JointRig):
    """Test getting a file part upload URL"""
    # First create a FileUploadBox
    box_id = await rig.create_default_box()

    # Then create a FileUpload within the box
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Now get the part upload URL
    part_no = 1
    result_url = await rig.controller.get_part_upload_url(
        file_id=file_id, part_no=part_no
    )

    # Verify the URL was returned
    assert result_url.startswith("https://storage.test/test-inbox/")


async def test_complete_file_upload(rig: JointRig):
    """Test completing a multipart file upload"""
    # First create a FileUploadBox
    box_id = await rig.create_default_box()

    # Then create a FileUpload within the box
    controller = rig.controller
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    file1_object_id = rig.file_upload_dao.latest.object_id

    # Now complete the file upload
    await controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{file1_object_id}",
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
    )
    bucket_id, object_storage = rig.object_storages.for_alias("test")
    assert await object_storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file1_object_id)
    )

    # Verify that the completed field was set on the FileUpload
    completed = now_utc_ms_prec()
    file_upload_dao = rig.file_upload_dao
    assert file_upload_dao.latest.id == file_id
    assert file_upload_dao.latest.completed is not None
    assert completed - file_upload_dao.latest.completed < timedelta(seconds=5)
    file_upload_box_dao = rig.file_upload_box_dao
    assert file_upload_box_dao.latest.size == DECRYPTED_SIZE
    assert file_upload_box_dao.latest.file_count == 1

    # Now repeat the process to ensure the box stats are incremented, not overwritten
    await sleep(MIN_SLEEP)
    other_decrypted_size = DECRYPTED_SIZE * 2  # this file is bigger
    other_encrypted_size = int(other_decrypted_size * 1.05)
    file_id2, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file2",
        decrypted_size=other_decrypted_size,
        encrypted_size=other_encrypted_size,
        part_size=PART_SIZE,
    )
    file2_object_id = rig.file_upload_dao.latest.object_id
    await controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id2,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{file2_object_id}",
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
    )
    latest_file_upload = file_upload_dao.latest
    assert latest_file_upload.id == file_id2
    assert latest_file_upload.completed
    assert latest_file_upload.completed > completed
    assert file_upload_box_dao.latest.file_count == 2
    assert file_upload_box_dao.latest.size == DECRYPTED_SIZE + other_decrypted_size


@pytest.mark.parametrize("complete_before_delete", [True, False])
async def test_delete_file_upload(rig: JointRig, complete_before_delete: bool):
    """Test deleting a FileUpload from a FileUploadBox"""
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao
    bucket_id, object_storage = rig.object_storages.for_alias("test")

    # First create a FileUploadBox
    box_id = await rig.create_default_box()

    # Then create a FileUpload within the box
    controller = rig.controller
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    object_id = str(rig.file_upload_dao.latest.object_id)

    assert await object_storage.list_multipart_uploads_for_object(
        bucket_id=bucket_id, object_id=object_id
    )

    if complete_before_delete:
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="unencrypted_checksum",
            encrypted_checksum=f"etag_for_{object_id}",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )
        assert file_upload_box_dao.latest.file_count == 1
        assert file_upload_box_dao.latest.size == DECRYPTED_SIZE
        assert await object_storage.does_object_exist(
            bucket_id=bucket_id, object_id=object_id
        )

    # Now delete the file upload
    await controller.remove_file_upload(box_id=box_id, file_id=file_id)
    assert not await object_storage.does_object_exist(
        bucket_id=bucket_id, object_id=object_id
    )

    assert not await object_storage.list_multipart_uploads_for_object(
        bucket_id=bucket_id, object_id=object_id
    )

    # FileUpload is set to "cancelled" (not removed from DB)
    assert len(file_upload_dao.resources) == 1
    assert file_upload_dao.latest.state == "cancelled"
    assert file_upload_box_dao.latest.file_count == 0
    assert file_upload_box_dao.latest.size == 0


async def test_update_box_max_size(rig: JointRig):
    """Test updating the max_size of a FileUploadBox"""
    file_upload_box_dao = rig.file_upload_box_dao
    box_id = await rig.create_default_box()

    new_max_size = TEST_MAX_BOX_SIZE * 2
    await rig.controller.update_box_max_size(
        box_id=box_id, version=0, max_size=new_max_size
    )

    assert file_upload_box_dao.latest.max_size == new_max_size
    assert file_upload_box_dao.latest.version == 1


async def test_update_box_max_size_errors(rig: JointRig):
    """Test that update_box_max_size raises the expected errors."""
    # BoxNotFound
    with pytest.raises(UploadControllerPort.BoxNotFoundError):
        await rig.controller.update_box_max_size(
            box_id=uuid4(), version=0, max_size=1234
        )

    # BoxVersionOutdated
    box_id = await rig.create_default_box()
    with pytest.raises(UploadControllerPort.BoxVersionError):
        await rig.controller.update_box_max_size(
            box_id=box_id, version=6, max_size=1234
        )


async def test_update_box_max_size_below_committed(rig: JointRig):
    """Test that setting max_size below committed bytes raises BoxMaxSizeTooLowError."""
    controller = rig.controller
    box_id = await rig.create_default_box()

    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    object_id = rig.file_upload_dao.latest.object_id
    await controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{object_id}",
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
    )

    box = rig.file_upload_box_dao.latest
    with pytest.raises(UploadControllerPort.BoxMaxSizeTooLowError):
        await controller.update_box_max_size(
            box_id=box_id, version=box.version, max_size=box.size - 1
        )


async def test_lock_file_upload_box(rig: JointRig):
    """Test locking an unlocked FileUploadBox"""
    # First create a FileUploadBox (starts open by default)
    file_upload_box_dao = rig.file_upload_box_dao
    box_id = await rig.create_default_box()

    # Verify the box starts open
    assert file_upload_box_dao.latest.state == "open"

    # Now lock the box
    await rig.controller.lock_file_upload_box(box_id=box_id, version=0)

    # Verify the box is now locked
    assert file_upload_box_dao.latest.state == "locked"


async def test_completion_recomputes_box_stats_from_truth(rig: JointRig):
    """Test that completing an upload derives box stats from the current FileUpload
    states, correcting any prior drift rather than blindly incrementing.
    """
    file_upload_box_dao = rig.file_upload_box_dao
    box_id = await rig.create_default_box()

    # Simulate out-of-sync size/file count on the box (version 0 -> 1)
    drifted_box = await file_upload_box_dao.get_by_id(box_id)
    drifted_box.file_count = 5
    drifted_box.size = 12345
    await file_upload_box_dao.update(drifted_box)

    # Complete one file upload so the box has real stats again
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    object_id = rig.file_upload_dao.latest.object_id
    await rig.controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{object_id}",
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
    )
    assert file_upload_box_dao.latest.file_count == 1
    assert file_upload_box_dao.latest.size == DECRYPTED_SIZE


async def test_lock_recomputes_box_stats(rig: JointRig):
    """Test that locking a box unconditionally recomputes its stats from the current
    FileUploads, correcting any prior drift in the same write that locks the box.
    """
    file_upload_box_dao = rig.file_upload_box_dao
    box_id = await rig.create_default_box()

    # Complete one upload so the box has a real, counted file (version 0 -> 1)
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    object_id = rig.file_upload_dao.latest.object_id
    await rig.controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{object_id}",
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
    )

    # Manufacture stat drift, then lock and confirm the lock write corrected it
    drifted_box = await file_upload_box_dao.get_by_id(box_id)
    drifted_box.file_count = 5
    drifted_box.size = 12345
    await file_upload_box_dao.update(drifted_box)

    await rig.controller.lock_file_upload_box(box_id=box_id, version=1)
    assert file_upload_box_dao.latest.state == "locked"
    assert file_upload_box_dao.latest.file_count == 1
    assert file_upload_box_dao.latest.size == DECRYPTED_SIZE


async def test_unlock_file_upload_box(rig: JointRig):
    """Test unlocking a locked FileUploadBox"""
    file_upload_box_dao = rig.file_upload_box_dao

    # First create a FileUploadBox
    box_id = await rig.create_default_box()

    # Lock the box first (version 0 → 1)
    await rig.controller.lock_file_upload_box(box_id=box_id, version=0)
    assert file_upload_box_dao.latest.state == "locked"

    # Now unlock the box (version 1 → 2)
    await rig.controller.unlock_file_upload_box(box_id=box_id, version=1)

    # Verify the box is now unlocked
    assert file_upload_box_dao.latest.state == "open"


async def test_lock_box_version_error(rig: JointRig):
    """Test that BoxVersionError is raised when the wrong version is supplied for lock."""
    box_id = await rig.create_default_box()

    with pytest.raises(UploadControllerPort.BoxVersionError) as exc_info:
        await rig.controller.lock_file_upload_box(box_id=box_id, version=99)

    assert str(box_id) in str(exc_info.value)
    # Box should remain unlocked
    assert rig.file_upload_box_dao.latest.state == "open"


async def test_unlock_box_version_error(rig: JointRig):
    """Test that BoxVersionError is raised when the wrong version is supplied for unlock."""
    box_id = await rig.create_default_box()
    await rig.controller.lock_file_upload_box(box_id=box_id, version=0)

    with pytest.raises(UploadControllerPort.BoxVersionError) as exc_info:
        await rig.controller.unlock_file_upload_box(box_id=box_id, version=0)

    assert str(box_id) in str(exc_info.value)
    # Box should remain locked
    assert rig.file_upload_box_dao.latest.state == "locked"


async def test_get_box_uploads(rig: JointRig):
    """Test getting file IDs for a given box ID"""
    # First create a FileUploadBox
    box_id = await rig.create_default_box()

    # Create multiple FileUploads within the box
    controller = rig.controller
    file_ids = []
    for i in range(3):
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias=f"file{i}",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
        )
        object_id = rig.file_upload_dao.latest.object_id
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="unencrypted_checksum",
            encrypted_checksum=f"etag_for_{object_id}",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )
        file_ids.append(file_id)

    # Create a second box with different files to test isolation
    other_box_id = await rig.create_default_box()
    other_file_ids = []
    for i in range(2):
        other_file_id, _ = await controller.initiate_file_upload(
            box_id=other_box_id,
            alias=f"file{i}",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
        )
        other_object_id = rig.file_upload_dao.latest.object_id
        await controller.complete_file_upload(
            box_id=other_box_id,
            file_id=other_file_id,
            unencrypted_checksum="unencrypted_checksum",
            encrypted_checksum=f"etag_for_{other_object_id}",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )
        other_file_ids.append(other_file_id)

    # Create a third, empty box
    empty_box_id = await rig.create_default_box()

    # Get the file uploads for the first box - should be sorted by alias by default
    file_uploads, total_count = await controller.get_box_file_info(box_id=box_id)
    assert len(file_uploads) == 3
    assert total_count == 3
    assert [r.alias for r in file_uploads] == ["file0", "file1", "file2"]
    assert all(r.id in file_ids for r in file_uploads)

    # The part checksum lists should be stripped by default
    assert all(r.encrypted_parts_md5 is None for r in file_uploads)
    assert all(r.encrypted_parts_sha256 is None for r in file_uploads)

    # The part checksum lists should be included when with_checksums is True,
    #  and stripping them must not have modified the stored data
    file_uploads, _ = await controller.get_box_file_info(
        box_id=box_id, with_checksums=True
    )
    assert all(r.encrypted_parts_md5 == ["abc123"] for r in file_uploads)
    assert all(r.encrypted_parts_sha256 == ["def456"] for r in file_uploads)

    # Get the file uploads sorted by alias in descending order
    file_uploads, total_count = await controller.get_box_file_info(
        box_id=box_id, sort=["-alias"]
    )
    assert total_count == 3
    assert [r.alias for r in file_uploads] == ["file2", "file1", "file0"]

    # When the sort spec doesn't reference alias, it should be appended. If it is
    #  included, then it shouldn't be appended.
    with patch.object(
        rig.file_upload_dao, "find_all", wraps=rig.file_upload_dao.find_all
    ) as find_all_spy:
        await controller.get_box_file_info(box_id=box_id, sort=["-state"])
        assert find_all_spy.call_args.kwargs["sort"] == ["-state", "alias"]
        await controller.get_box_file_info(
            box_id=box_id, sort=["-state", "-alias", "decrypted_size"]
        )
        assert find_all_spy.call_args.kwargs["sort"] == [
            "-state",
            "-alias",
            "decrypted_size",
        ]

    # Verify the other box returns only its own files
    other_uploads, other_total = await controller.get_box_file_info(box_id=other_box_id)
    assert len(other_uploads) == 2
    assert other_total == 2
    assert all(r.id in other_file_ids for r in other_uploads)

    # Verify that we get an empty list for the third box
    empty_uploads, empty_total = await controller.get_box_file_info(box_id=empty_box_id)
    assert empty_uploads == []
    assert empty_total == 0


async def test_get_box_uploads_retrieves_all_states(rig: JointRig):
    """Make sure that get_box_file_info() lists all files regardless of state"""
    # First create a FileUploadBox
    box_id = await rig.create_default_box()
    storage_alias = next(iter(rig.config.object_storages))
    states: list[FileUploadState] = sorted(
        [
            "interrogated",
            "awaiting_archival",
            "archived",
            "cancelled",
            "failed",
            "inbox",
            "init",
        ]
    )
    for state in states:
        file_upload = FileUpload(
            id=uuid4(),
            box_id=box_id,
            alias=state,
            state=state,
            s3_upload_id=f"upload_for_{state}.vcf",
            state_updated=now_utc_ms_prec(),
            storage_alias=storage_alias,
            bucket_id="bucket1",
            object_id=uuid4(),
            decrypted_sha256="decrypted_hash",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
            initiated=now_utc_ms_prec(),
        )
        await rig.file_upload_dao.insert(file_upload)

    files, total = await rig.controller.get_box_file_info(box_id=box_id)
    assert [f.alias for f in files] == states
    assert total == len(states)


async def test_create_box_with_unknown_storage_alias(rig: JointRig):
    """Test for error handling when the user tries to create new FileUploadBox
    with a storage alias that isn't configured.
    """
    # Try to create a FileUploadBox with an unknown storage alias
    controller = rig.controller
    unknown_storage_alias = "unknown_storage_alias_that_does_not_exist"

    # Should raise UnknownStorageAliasError
    with pytest.raises(UploadControllerPort.UnknownStorageAliasError) as exc_info:
        await controller.create_file_upload_box(
            storage_alias=unknown_storage_alias, max_size=TEST_MAX_BOX_SIZE
        )

    # Verify the exception message contains the storage alias
    assert unknown_storage_alias in str(exc_info.value)

    # Verify no box was created in the DAO
    assert not rig.file_upload_box_dao.resources


async def test_create_file_upload_when_box_missing(rig: JointRig):
    """Test error handling in the case where the user tries to create a FileUpload
    for a box ID that doesn't exist.
    """
    controller = rig.controller

    # Try to create a FileUpload for a non-existent box
    non_existent_box_id = uuid4()

    # Should raise BoxNotFoundError
    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await controller.initiate_file_upload(
            box_id=non_existent_box_id,
            alias="test_file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
        )

    # Verify the exception contains the correct box_id
    assert str(non_existent_box_id) in str(exc_info.value)

    # Verify no FileUpload was created
    assert not rig.file_upload_dao.resources


async def test_create_file_upload_when_box_locked(rig: JointRig):
    """Test error handling in the case where the user tries to create a FileUpload
    in a locked FileUploadBox.
    """
    file_upload_box_dao = rig.file_upload_box_dao

    # First create a FileUploadBox and lock it (version 0 → 1)
    box_id = await rig.create_default_box()
    await rig.controller.lock_file_upload_box(box_id=box_id, version=0)
    assert file_upload_box_dao.latest.state == "locked"

    # Try to create a FileUpload in the locked box - should raise BoxStateError
    with pytest.raises(UploadControllerPort.BoxStateError) as exc_info:
        await rig.controller.initiate_file_upload(
            box_id=box_id,
            alias="test_file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
        )

    # Verify the exception contains the correct box_id
    assert str(box_id) in str(exc_info.value)

    # Verify no FileUpload was created
    assert not rig.file_upload_dao.resources


async def test_delete_file_upload_when_box_missing(rig: JointRig):
    """Test error handling in the case where the user tries to delete a FileUpload
    for a box ID that doesn't exist.
    """
    controller = rig.controller

    # Try to delete a FileUpload from a non-existent box
    non_existent_box_id = uuid4()
    fake_file_id = uuid4()

    # Should raise BoxNotFoundError
    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await controller.remove_file_upload(
            box_id=non_existent_box_id, file_id=fake_file_id
        )

    # Verify the exception contains the correct box_id
    assert str(non_existent_box_id) in str(exc_info.value)

    # Verify no changes were made to DAOs
    assert not rig.file_upload_box_dao.resources
    assert not rig.file_upload_dao.resources


async def test_delete_file_upload_when_box_locked(rig: JointRig):
    """Test error handling in the case where the user tries to delete a FileUpload
    in a locked FileUploadBox.
    """
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao

    # First create a FileUploadBox and FileUpload
    box_id = await rig.create_default_box()
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Lock the box manually by updating the state
    box = await file_upload_box_dao.get_by_id(box_id)
    box.state = "locked"
    await file_upload_box_dao.update(box)
    assert file_upload_box_dao.latest.state == "locked"

    # Try to delete the FileUpload from the locked box - should raise BoxStateError
    with pytest.raises(UploadControllerPort.BoxStateError) as exc_info:
        await controller.remove_file_upload(box_id=box_id, file_id=file_id)

    # Verify the exception contains the correct box_id
    assert str(box_id) in str(exc_info.value)

    # Verify the FileUpload still exists (wasn't deleted)
    assert len(file_upload_dao.resources) == 1


@pytest.mark.parametrize(
    "state",
    [
        "interrogated",
        "awaiting_archival",
        "archived",
        "cancelled",
        "failed",
        "inbox",
        "init",
    ],
)
async def test_remove_file_upload_skips_s3_for_terminal_states(
    rig: JointRig,
    monkeypatch: pytest.MonkeyPatch,
    state: FileUploadState,
):
    """Test that remove_file_upload makes no S3 calls for FileUploads in states that
    are past the multipart upload phase (interrogated, awaiting_archival, archived) or
    already in a terminal state (cancelled, failed).

    Also checks correct calls for inbox and init states for completeness.
    """
    box_id = await rig.create_default_box()
    file_upload = make_file_upload(state=state)
    file_upload.box_id = box_id
    await rig.file_upload_dao.insert(file_upload)

    s3_calls: list[str] = []

    async def spy_delete_inbox_file(**kwargs):
        s3_calls.append("delete_inbox_file")

    async def spy_abort_multipart_upload(**kwargs):
        s3_calls.append("abort_multipart_upload")

    monkeypatch.setattr(rig.s3_client, "delete_inbox_file", spy_delete_inbox_file)
    monkeypatch.setattr(
        rig.s3_client, "abort_multipart_upload", spy_abort_multipart_upload
    )

    # Call remove_file_upload() and verify that the S3Client's delete method wasn't called
    await rig.controller.remove_file_upload(box_id=box_id, file_id=file_upload.id)

    if state in ["inbox", "init"]:
        assert s3_calls == (
            ["delete_inbox_file"] if state == "inbox" else ["abort_multipart_upload"]
        )
    else:
        assert not s3_calls, (
            f"Expected no S3 calls for state '{state}', but got: {s3_calls}"
        )
    updated_upload = await rig.file_upload_dao.get_by_id(file_upload.id)
    assert updated_upload.state == "cancelled"


async def test_remove_file_upload_when_upload_missing(rig: JointRig):
    """Test error handling in the case where the user tries to delete a FileUpload
    that doesn't exist.
    """
    # Create a FileUploadBox
    box_id = await rig.create_default_box()

    # Try to delete a FileUpload that doesn't exist - should raise FileUploadNotFound
    with pytest.raises(UploadControllerPort.FileUploadNotFound):
        await rig.controller.remove_file_upload(box_id=box_id, file_id=uuid4())


async def test_delete_file_upload_with_s3_error(rig: JointRig):
    """Test for error handling when the user tries to delete a FileUpload
    but gets an S3 error in the process of aborting an ongoing upload.
    """
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload
    box_id = await rig.create_default_box()
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Set the mock to raise a MultiPartUploadAbortError
    # This simulates S3 failing to abort the multipart upload
    # Try to delete the file upload - should raise UploadAbortError
    storage = rig.object_storages.for_alias("test")[1]

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadAbortError("", "", "")

    storage.abort_multipart_upload = do_error
    with pytest.raises(UploadControllerPort.UploadAbortError) as exc_info:
        await controller.remove_file_upload(box_id=box_id, file_id=file_id)

    # Verify the exception contains the S3 upload ID
    s3_upload_id = rig.file_upload_dao.latest.s3_upload_id
    assert s3_upload_id in str(exc_info.value)

    # Verify the FileUpload still exists (deletion failed)
    assert len(rig.file_upload_dao.resources) == 1


async def test_unlock_missing_box(rig: JointRig):
    """Test error handling for case where the user tries to unlock a missing box."""
    controller = rig.controller

    # Try to unlock a non-existent box
    non_existent_box_id = uuid4()
    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await controller.unlock_file_upload_box(box_id=non_existent_box_id, version=0)

    # Verify the exception contains the correct box_id
    assert str(non_existent_box_id) in str(exc_info.value)


async def test_lock_missing_box(rig: JointRig):
    """Test error handling for case where the user tries to lock a missing box."""
    controller = rig.controller

    # Try to lock a non-existent box
    non_existent_box_id = uuid4()

    # Should raise BoxNotFoundError
    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await controller.lock_file_upload_box(box_id=non_existent_box_id, version=0)

    # Verify the exception contains the correct box_id
    assert str(non_existent_box_id) in str(exc_info.value)


async def test_lock_box_with_incomplete_upload(rig: JointRig):
    """Test error handling for the scenario where the user tries to lock a box
    for which incomplete FileUpload(s) exist.
    """
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao

    # Create a FileUploadBox and a FileUpload
    box_id = await rig.create_default_box()

    file_id1, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    file_id2, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file2",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    # Attempt to lock the box while the upload is still incomplete
    with pytest.raises(UploadControllerPort.IncompleteUploadsError) as exc_info:
        await controller.lock_file_upload_box(box_id=box_id, version=0)

    # Verify the exception carries the right IDs and aliases (sorted by alias)
    assert exc_info.value.file_ids == [
        (file_id1, "test_file"),
        (file_id2, "test_file2"),
    ]

    # Verify that the box is still open
    assert file_upload_box_dao.latest.state == "open"


@pytest.mark.parametrize("terminal_state", ["failed", "cancelled"])
async def test_lock_box_ignores_terminal_uploads(
    rig: JointRig, terminal_state: FileUploadState
):
    """Locking with force=False must succeed when the only incomplete uploads
    (inbox_upload_completed=False) are in a terminal state (failed/cancelled).
    Those uploads are no longer active. The only state that should block locking
    is 'init'.
    """
    box_id = await rig.create_default_box()

    file_upload = make_file_upload(state=terminal_state)
    file_upload.box_id = box_id
    await rig.file_upload_dao.insert(file_upload)

    await rig.controller.lock_file_upload_box(box_id=box_id, version=0)
    assert rig.file_upload_box_dao.latest.state == "locked"


async def test_complete_file_upload_when_box_missing(rig: JointRig):
    """Test error handling in the case where the user tries to complete a FileUpload
    for a box ID that doesn't exist.
    """
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao

    # Create a FileUploadBox and a FileUpload
    box_id = await rig.create_default_box()
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Manually delete the box (simulating a scenario where the box was deleted
    # but the file upload and S3 details remain orphaned)
    await file_upload_box_dao.delete(box_id)

    # Verify the box is gone but file upload and S3 details remain
    assert not file_upload_box_dao.resources
    assert len(file_upload_dao.resources) == 1

    # Try to complete the file upload for the now missing box
    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await rig.controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum="sha256:encrypted_checksum_here",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    # Verify the exception contains the correct box_id
    assert str(box_id) in str(exc_info.value)


@pytest.mark.parametrize("terminal_state", ["cancelled", "failed"])
async def test_complete_file_upload_in_terminal_state(
    rig: JointRig, terminal_state: FileUploadState
):
    """Completing a cancelled or failed FileUpload must raise FileUploadStateError
    rather than attempting the S3 operation on an already-aborted or invalid upload.
    """
    box_id = await rig.create_default_box()
    file_upload = make_file_upload(state=terminal_state)
    file_upload.box_id = box_id
    await rig.file_upload_dao.insert(file_upload)

    with pytest.raises(UploadControllerPort.FileUploadStateError) as exc_info:
        await rig.controller.complete_file_upload(
            box_id=box_id,
            file_id=file_upload.id,
            unencrypted_checksum="sha256:checksum",
            encrypted_checksum="md5:checksum",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    assert str(file_upload.id) in str(exc_info.value)
    assert terminal_state in str(exc_info.value)


async def test_complete_missing_file_upload(rig: JointRig):
    """Test error handling in the case where the user tries to complete a FileUpload
    that doesn't exist.
    """
    # Create a box first
    box_id = await rig.create_default_box()

    # Try to complete a file upload that doesn't exist
    non_existent_file_id = uuid4()

    with pytest.raises(UploadControllerPort.FileUploadNotFound) as exc_info:
        await rig.controller.complete_file_upload(
            box_id=box_id,
            file_id=non_existent_file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum="sha256:encrypted_checksum_here",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )
    assert not rig.file_upload_dao.resources

    # Verify the exception contains the correct file_id
    assert str(non_existent_file_id) in str(exc_info.value)


async def test_complete_file_upload_with_unknown_storage_alias(rig: JointRig):
    """Test for error handling when the user tries to complete a FileUpload
    with a storage alias that isn't configured.
    """
    file_upload_dao = rig.file_upload_dao
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload with a valid storage alias
    box_id = await rig.create_default_box()
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Verify the FileUpload was created
    assert len(file_upload_dao.resources) == 1

    # Manually modify the FileUpload to have an unknown storage alias
    # This simulates a scenario where configuration changed or data was corrupted
    file_upload = file_upload_dao.latest
    file_upload.storage_alias = "does_not_exist"
    await file_upload_dao.update(file_upload)

    # Try to complete the file upload - should raise UnknownStorageAliasError
    with pytest.raises(UploadControllerPort.UnknownStorageAliasError) as exc_info:
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum="sha256:encrypted_checksum_here",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    # Verify the exception message contains the unknown storage alias
    assert "does_not_exist" in str(exc_info.value)
    assert rig.file_upload_box_dao.latest.size == 0
    assert rig.file_upload_box_dao.latest.file_count == 0


async def test_complete_file_upload_with_s3_error(rig: JointRig):
    """Test for error handling when the user tries to complete a FileUpload
    but gets an S3 error in the process.
    """
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload
    box_id = await rig.create_default_box()
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Set the mock to raise a MultiPartUploadConfirmError
    # This simulates S3 failing to complete the multipart upload
    # Try to complete the file upload - should raise UploadCompletionError
    storage = rig.object_storages.for_alias("test")[1]

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadConfirmError("", "", "")

    storage.complete_multipart_upload = do_error
    with pytest.raises(UploadControllerPort.UploadCompletionError) as exc_info:
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum=f"etag_for_{file_id}",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    # Verify the exception contains the S3 upload ID
    s3_upload_id = file_upload_dao.latest.s3_upload_id
    assert s3_upload_id in str(exc_info.value)
    assert not file_upload_dao.latest.completed
    assert file_upload_box_dao.latest.size == 0
    assert file_upload_box_dao.latest.file_count == 0


async def test_complete_file_upload_size_mismatch(rig: JointRig):
    """Test that UploadSizeMismatchError is raised and the FileUpload is marked 'failed'
    when the actual S3 object size doesn't match the declared encrypted_size.
    """
    box_id = await rig.create_default_box()
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    file_upload = rig.file_upload_dao.latest
    assert file_upload.state == "init"
    state_updated = file_upload.state_updated

    # Sleep so we can check for the timestamp difference
    await sleep(MIN_SLEEP)

    # Patch get_object_size to return a wrong size for this object
    _, storage = rig.object_storages.for_alias("test")

    async def wrong_size(*args, **kwargs):
        return ENCRYPTED_SIZE + 1

    storage.get_object_size = wrong_size

    # Now try to complete the upload. Should get the UploadSizeMismatchError.
    object_id = rig.file_upload_dao.latest.object_id
    with pytest.raises(UploadControllerPort.UploadSizeMismatchError):
        await rig.controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum=f"etag_for_{object_id}",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    # Make sure the FileUpload attributes are updated
    file_upload = rig.file_upload_dao.latest
    assert file_upload.state == "failed"
    assert file_upload.state_updated > state_updated
    assert not file_upload.completed
    assert rig.file_upload_box_dao.latest.size == 0
    assert rig.file_upload_box_dao.latest.file_count == 0


async def test_complete_file_upload_checksum_mismatch(rig: JointRig):
    """Test to make sure the FileUpload is marked as 'failed' if the UploadController
    raises a ChecksumMismatchError.
    """
    file_upload_box_dao = rig.file_upload_box_dao
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload
    box_id = await rig.create_default_box()
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    file_upload = rig.file_upload_dao.latest
    assert file_upload.state == "init"
    state_updated = file_upload.state_updated

    await sleep(MIN_SLEEP)  # short sleep for differentiating timestamps

    # Provide a wrong checksum to trigger a ChecksumMismatchError
    with pytest.raises(UploadControllerPort.ChecksumMismatchError):
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum="wrong_checksum",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    file_upload = rig.file_upload_dao.latest
    assert file_upload.state == "failed"
    assert file_upload.state_updated > state_updated
    assert not file_upload.completed
    assert file_upload_box_dao.latest.size == 0
    assert file_upload_box_dao.latest.file_count == 0


async def test_get_part_upload_url_with_unknown_storage_alias(rig: JointRig):
    """Test for error handling when getting a part URL but the storage alias found in
    the FileUpload is unknown (maybe configuration changed or data was migrated wrong).
    """
    # Create a FileUploadBox and a FileUpload with a valid storage alias
    controller = rig.controller
    box_id = await rig.create_default_box()
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Manually modify the FileUpload to have an unknown storage alias
    # This simulates a scenario where configuration changed or data was corrupted
    file_upload = rig.file_upload_dao.latest
    file_upload.storage_alias = "unknown_storage_alias"
    await rig.file_upload_dao.update(file_upload)

    # Try to get a part upload URL - should raise UnknownStorageAliasError
    with pytest.raises(UploadControllerPort.UnknownStorageAliasError) as exc_info:
        await controller.get_part_upload_url(file_id=file_id, part_no=1)

    # Verify the exception message contains the unknown storage alias
    assert "unknown_storage_alias" in str(exc_info.value)


async def test_get_part_upload_url_when_s3_upload_not_found(rig: JointRig):
    """Test for error handling when getting a part URL but S3 raises an error saying
    that it can't find the corresponding multipart upload on its end.
    """
    # Create a FileUploadBox and a FileUpload
    controller = rig.controller
    box_id = await rig.create_default_box()
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Set the mock to raise a MultiPartUploadNotFoundError
    # This simulates S3 not being able to find the multipart upload
    # Try to get a part upload URL - should raise S3UploadNotFoundError
    storage = rig.object_storages.for_alias("test")[1]

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadNotFoundError("", "", "")

    storage.get_part_upload_url = do_error
    with pytest.raises(UploadControllerPort.UploadSessionNotFoundError) as exc_info:
        await controller.get_part_upload_url(file_id=file_id, part_no=1)

    # Verify the exception contains the S3 upload ID
    s3_upload_id = rig.file_upload_dao.latest.s3_upload_id
    assert s3_upload_id in str(exc_info.value)


async def test_get_file_ids_for_non_existent_box(rig: JointRig):
    """Test get_file_ids_for_box with a non-existent box ID."""
    with pytest.raises(UploadControllerPort.BoxNotFoundError):
        await rig.controller.get_box_file_info(box_id=uuid4())


async def test_get_box_file_info_pagination_error(
    rig: JointRig, monkeypatch: pytest.MonkeyPatch
):
    """Test that a ValueError raised by the DAO's find_all is translated to PaginationError."""
    box_id = await rig.create_default_box()
    with pytest.raises(UploadControllerPort.PaginationError):
        await rig.controller.get_box_file_info(box_id=box_id, skip=-1)


async def test_process_interrogation_success_no_file_upload(rig: JointRig):
    """Test the alt case where the file upload doesn't exist."""
    non_existent_file_id = uuid4()
    report = InterrogationSuccess(
        file_id=non_existent_file_id,
        secret_id="test-secret-456",
        storage_alias="test",
        bucket_id="test-inbox",
        object_id=uuid4(),
        interrogated_at=now_utc_ms_prec(),
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
        encrypted_size=ENCRYPTED_SIZE,
    )

    with pytest.raises(UploadControllerPort.FileUploadNotFound):
        await rig.controller.process_interrogation_success(report=report)


async def test_initiate_upload_after_failed(rig: JointRig):
    """Re-initiating an upload with the same alias is allowed when the existing
    FileUpload is in 'failed' state.
    """
    controller = rig.controller
    file_upload_dao = rig.file_upload_dao

    box_id = await rig.create_default_box()
    file_id_1, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Simulate the "failed" state directly
    file_upload = await file_upload_dao.get_by_id(file_id_1)
    file_upload.state = "failed"
    await file_upload_dao.update(file_upload)

    # Patch insert to simulate the MongoDB compound-index constraint violation
    original_insert = file_upload_dao.insert
    call_count = 0

    async def patched_insert(dto):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise UniqueConstraintViolationError(
                unique_fields={"box_id": str(box_id), "alias": "test_file"}
            )
        return await original_insert(dto)

    file_upload_dao.insert = patched_insert

    file_id_2, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    assert file_id_2 != file_id_1
    assert len(file_upload_dao.resources) == 1
    new_upload = await file_upload_dao.get_by_id(file_id_2)
    assert new_upload.state == "init"
    assert new_upload.alias == "test_file"


async def test_initiate_upload_after_cancelled(rig: JointRig):
    """Re-initiating an upload with the same alias is allowed when the existing
    FileUpload is in 'cancelled' state.
    """
    controller = rig.controller
    file_upload_dao = rig.file_upload_dao

    box_id = await rig.create_default_box()
    file_id_1, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    await controller.remove_file_upload(box_id=box_id, file_id=file_id_1)

    cancelled = await file_upload_dao.get_by_id(file_id_1)
    assert cancelled.state == "cancelled"

    original_insert = file_upload_dao.insert
    call_count = 0

    async def patched_insert(dto):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise UniqueConstraintViolationError(
                unique_fields={"box_id": str(box_id), "alias": "test_file"}
            )
        return await original_insert(dto)

    file_upload_dao.insert = patched_insert

    file_id_2, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    assert file_id_2 != file_id_1
    assert len(file_upload_dao.resources) == 1
    new_upload = await file_upload_dao.get_by_id(file_id_2)
    assert new_upload.state == "init"
    assert new_upload.s3_upload_id != cancelled.s3_upload_id


async def test_initiate_upload_blocked_for_inbox_state(rig: JointRig):
    """Re-initiating an upload with the same alias is blocked when the existing
    FileUpload is in 'inbox' state (active upload, not a retryable terminal state).
    """
    controller = rig.controller
    file_upload_dao = rig.file_upload_dao

    box_id = await rig.create_default_box()
    file_id_1, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    object_id_1 = rig.file_upload_dao.latest.object_id
    await controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id_1,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{object_id_1}",
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
    )

    inbox_upload = await file_upload_dao.get_by_id(file_id_1)
    assert inbox_upload.state == "inbox"

    async def patched_insert(dto):
        raise UniqueConstraintViolationError(
            unique_fields={"box_id": str(box_id), "alias": "test_file"}
        )

    file_upload_dao.insert = patched_insert

    with pytest.raises(UploadControllerPort.FileUploadAlreadyExists):
        await controller.initiate_file_upload(
            box_id=box_id,
            alias="test_file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
        )

    # Original FileUpload must be untouched
    assert len(file_upload_dao.resources) == 1
    assert (await file_upload_dao.get_by_id(file_id_1)).state == "inbox"


@pytest.mark.parametrize("state", ["init", "inbox"])
async def test_overwrite_cancels_active_upload(
    rig: JointRig,
    state: FileUploadState,
):
    """Test that when overwrite=True, an active FileUpload in 'init' or 'inbox' state is
    cancelled and replaced by a new one for the same alias without raising an error.
    """
    controller = rig.controller
    file_upload_dao = rig.file_upload_dao
    bucket_id, object_storage = rig.object_storages.for_alias("test")

    box_id = await rig.create_default_box()
    file_id_1, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    object_id_1 = str(rig.file_upload_dao.latest.object_id)

    if state == "inbox":
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id_1,
            unencrypted_checksum="unencrypted_checksum",
            encrypted_checksum=f"etag_for_{object_id_1}",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )
        assert (await file_upload_dao.get_by_id(file_id_1)).state == "inbox"

    file_id_2, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
        overwrite=True,
    )

    assert file_id_2 != file_id_1

    # Old upload should be cancelled now
    old_upload = await file_upload_dao.get_by_id(file_id_1)
    assert old_upload.state == "cancelled"

    # New upload should be in 'init' state
    new_upload = await file_upload_dao.get_by_id(file_id_2)
    assert new_upload.state == "init"
    assert new_upload.alias == "test_file"

    # S3 resources for the old upload should have been cleaned up
    if state == "init":
        assert not await object_storage.list_multipart_uploads_for_object(
            bucket_id=bucket_id, object_id=object_id_1
        )
    else:
        assert not await object_storage.does_object_exist(
            bucket_id=bucket_id, object_id=object_id_1
        )


@pytest.mark.parametrize(
    "state",
    ["interrogated", "awaiting_archival", "archived"],
)
async def test_overwrite_blocked_for_immutable_states(
    rig: JointRig,
    state: FileUploadState,
):
    """Test that when overwrite=True, uploads in 'interrogated', 'awaiting_archival', or
    'archived' state cannot be replaced and FileUploadAlreadyExists is raised.

    The InMemDao doesn't enforce compound unique indexes, so we simulate the
    MongoDB UniqueConstraintViolationError the same way existing idempotence tests do.
    """
    controller = rig.controller
    file_upload_dao = rig.file_upload_dao

    box_id = await rig.create_default_box()

    # Insert a FileUpload directly in the non-overwritable state
    file_upload = make_file_upload(state=state)
    file_upload.box_id = box_id
    file_upload.alias = "test_file"
    await file_upload_dao.insert(file_upload)

    # Simulate the compound unique index violation MongoDB would raise on insert
    async def patched_insert(dto):
        raise UniqueConstraintViolationError(
            unique_fields={"box_id": str(box_id), "alias": "test_file"}
        )

    file_upload_dao.insert = patched_insert

    with pytest.raises(UploadControllerPort.FileUploadAlreadyExists):
        await controller.initiate_file_upload(
            box_id=box_id,
            alias="test_file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
            overwrite=True,
        )

    # Original FileUpload must be untouched
    assert len(file_upload_dao.resources) == 1
    assert (await file_upload_dao.get_by_id(file_upload.id)).state == state


@pytest.mark.parametrize("state", ["init", "inbox"])
async def test_overwrite_false_still_blocks_active_upload(
    rig: JointRig, state: FileUploadState
):
    """With overwrite=False (default), an active 'init' or 'inbox' upload still raises
    FileUploadAlreadyExists, confirming overwrite is opt-in.

    The InMemDao doesn't enforce compound unique indexes, so we simulate the
    MongoDB UniqueConstraintViolationError the same way existing idempotence tests do.
    """
    controller = rig.controller
    file_upload_dao = rig.file_upload_dao

    box_id = await rig.create_default_box()
    file_id_1, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    if state == "inbox":
        file_upload = file_upload_dao.latest
        file_upload.state = "inbox"
        await file_upload_dao.update(file_upload)
        assert file_upload_dao.latest.state == "inbox"

    # Simulate the compound unique index violation MongoDB would raise on insert
    async def patched_insert(dto):
        raise UniqueConstraintViolationError(
            unique_fields={"box_id": str(box_id), "alias": "test_file"}
        )

    file_upload_dao.insert = patched_insert

    with pytest.raises(UploadControllerPort.FileUploadAlreadyExists):
        await controller.initiate_file_upload(
            box_id=box_id,
            alias="test_file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
            overwrite=False,
        )

    # First upload must be untouched and still in 'init'
    upload = await file_upload_dao.get_by_id(file_id_1)
    assert upload.state == state


@pytest.mark.parametrize(
    "max_size, pre_existing_sizes, expect_error",
    [
        (DECRYPTED_SIZE, [], False),
        (DECRYPTED_SIZE - 1, [], True),
        (DECRYPTED_SIZE * 2, [DECRYPTED_SIZE, DECRYPTED_SIZE], True),
    ],
    ids=["at_exact_limit", "one_byte_over", "aggregate_exceeded"],
)
async def test_box_size_limit(
    rig: JointRig,
    max_size: int,
    pre_existing_sizes: list[int],
    expect_error: bool,
):
    """Box size limit: at the exact limit (no error), one byte over (error),
    and aggregate in-progress uploads that push the total over the limit (error).
    """
    controller = rig.controller
    box_id = await controller.create_file_upload_box(
        storage_alias="test", max_size=max_size
    )
    for i, size in enumerate(pre_existing_sizes):
        await controller.initiate_file_upload(
            box_id=box_id,
            alias=f"existing_{i}",
            decrypted_size=size,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
        )

    with (
        pytest.raises(UploadControllerPort.BoxMaxSizeExceededError)
        if expect_error
        else nullcontext()
    ):
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="new_file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
        )
        assert rig.file_upload_dao.latest.id == file_id


async def test_finished_uploads_count_toward_limit(rig: JointRig):
    """Test that when calculating the progress towards the size quota, completed uploads
    are also taken into account rather than only the in-progress uploads. Also check
    that failed and cancelled uploads are ignored.
    """
    controller = rig.controller
    # Box fits exactly 2 files
    box_id = await controller.create_file_upload_box(
        storage_alias="test", max_size=DECRYPTED_SIZE * 2
    )
    # Upload and complete file1 — now box.size == DECRYPTED_SIZE
    file_id1, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="file1",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    await controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id1,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{rig.file_upload_dao.latest.object_id}",
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
    )
    assert rig.file_upload_box_dao.latest.size == DECRYPTED_SIZE

    # file2 fits exactly (box.size + 0 init + DECRYPTED_SIZE == max_size)
    file_id2, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="file2",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # file3 would exceed: box.size (DECRYPTED_SIZE) + in_progress (DECRYPTED_SIZE) + new > max
    with pytest.raises(UploadControllerPort.BoxMaxSizeExceededError):
        await controller.initiate_file_upload(
            box_id=box_id,
            alias="file3",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=PART_SIZE,
        )

    # Cancel file2. quota consumption stays at DECRYPTED_SIZE (only file1 counts now)
    await controller.remove_file_upload(box_id=box_id, file_id=file_id2)
    assert rig.file_upload_box_dao.latest.size == DECRYPTED_SIZE

    # Create an upload and mark it as failed to show failed uploads are also ignored.
    failed_file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="failed_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    failed_upload = await rig.file_upload_dao.get_by_id(failed_file_id)
    failed_upload.state = "failed"
    await rig.file_upload_dao.update(failed_upload)

    # file3 now fits: box.size (DECRYPTED_SIZE) + 0 in-progress + DECRYPTED_SIZE == max_size.
    # The cancelled file2 and the failed upload are both excluded from the calculation.
    file_id3, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="file3",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    assert rig.file_upload_dao.latest.id == file_id3


async def test_concurrent_upload_cap(rig: JointRig):
    """Concurrent upload cap by trying to create a new FileUpload when the current
    file count is below the limit and at the limit.
    """
    limit = rig.config.max_concurrent_uploads_per_box
    box_id = await rig.controller.create_file_upload_box(
        storage_alias="test", max_size=TEST_MAX_BOX_SIZE
    )
    # Use all of our in-flight quota
    for i in range(limit):
        _ = await rig.controller.initiate_file_upload(
            box_id=box_id,
            alias=f"existing_{i}",
            decrypted_size=1,
            encrypted_size=1,
            part_size=PART_SIZE,
        )

    # Trigger the new error by trying to start another upload
    with pytest.raises(UploadControllerPort.TooManyOpenUploadsError):
        _ = await rig.controller.initiate_file_upload(
            box_id=box_id,
            alias="new_file",
            decrypted_size=1,
            encrypted_size=1,
            part_size=PART_SIZE,
        )

    # Now complete a file to free up a slot
    await rig.controller.complete_file_upload(
        box_id=box_id,
        file_id=rig.file_upload_dao.latest.id,
        unencrypted_checksum="abc",
        encrypted_checksum=f"etag_for_{rig.file_upload_dao.latest.object_id}",
        encrypted_parts_md5=["a1", "b2"],
        encrypted_parts_sha256=["a1", "b2"],
    )

    # Test that we can now upload a file again
    _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="new_file",
        decrypted_size=1,
        encrypted_size=1,
        part_size=PART_SIZE,
    )

    # And finally check that crossing the limit once again triggers the error
    # Trigger the new error by trying to start another upload
    with pytest.raises(UploadControllerPort.TooManyOpenUploadsError):
        _ = await rig.controller.initiate_file_upload(
            box_id=box_id,
            alias="new_file",
            decrypted_size=1,
            encrypted_size=1,
            part_size=PART_SIZE,
        )


@pytest.mark.parametrize(
    "part_size, encrypted_size, expect_error",
    [
        (PART_SIZE, ENCRYPTED_SIZE, False),
        (0, ENCRYPTED_SIZE, True),
        (MIN_PART_SIZE - 1, ENCRYPTED_SIZE, True),
        (MAX_PART_SIZE + 1, ENCRYPTED_SIZE, True),
        (MIN_PART_SIZE, MIN_PART_SIZE * (MAX_PART_COUNT + 1), True),
    ],
    ids=["valid", "zero", "too_small", "too_large", "too_many_parts"],
)
async def test_part_size_validation(
    rig: JointRig,
    part_size: int,
    encrypted_size: int,
    expect_error: bool,
):
    """Test the part size validation with the happy path and the failure modes."""
    box_id = await rig.create_default_box()
    with (
        pytest.raises(UploadControllerPort.PartSizeError)
        if expect_error
        else nullcontext()
    ):
        _, _ = await rig.controller.initiate_file_upload(
            box_id=box_id,
            alias="test_file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=encrypted_size,
            part_size=part_size,
        )


def _make_matching_event(file_upload: FileUpload) -> FileInternallyRegistered:
    """Create a FileInternallyRegistered event that matches the given FileUpload."""
    return FileInternallyRegistered(
        file_id=file_upload.id,
        archive_date=now_utc_ms_prec(),
        storage_alias=file_upload.storage_alias,
        bucket_id="permanent",
        secret_id=file_upload.secret_id,
        decrypted_size=file_upload.decrypted_size,
        encrypted_size=file_upload.encrypted_size,
        decrypted_sha256=file_upload.decrypted_sha256,
        encrypted_parts_md5=file_upload.encrypted_parts_md5,
        encrypted_parts_sha256=file_upload.encrypted_parts_sha256,
        part_size=file_upload.part_size,
    )


async def test_handle_internal_file_registration(rig: JointRig):
    """Test that process_internal_file_registration sets state to 'archived' and
    updates state_updated on a FileUpload that is in 'awaiting_archival' state.

    Then the method is re-run to test idempotence.
    """
    # Create the FileUpload and matching FileInternallyRegistered event, but don't
    #  insert the FileUpload just yet. First, check for error handling on absent FileUploads
    file_upload = make_file_upload(state="awaiting_archival")
    event = _make_matching_event(file_upload)
    with pytest.raises(UploadControllerPort.FileUploadNotFound):
        await rig.controller.process_internal_file_registration(
            registration_metadata=event
        )

    # Now insert the FileUpload and run the event handling function
    await rig.file_upload_dao.insert(file_upload)

    await sleep(MIN_SLEEP)  # sleep so that timestamp comparisons are valid
    await rig.controller.process_internal_file_registration(registration_metadata=event)
    updated_file_upload = await rig.file_upload_dao.get_by_id(file_upload.id)
    assert updated_file_upload.state == "archived"
    assert updated_file_upload.state_updated > file_upload.state_updated

    # Now reprocess the event - should get no errors and timestamp should be unchanged
    await sleep(MIN_SLEEP)  # sleep so that timestamp comparisons are valid
    await rig.controller.process_internal_file_registration(registration_metadata=event)
    final_file_upload = await rig.file_upload_dao.get_by_id(file_upload.id)
    assert final_file_upload.state == "archived"
    assert final_file_upload.state_updated == updated_file_upload.state_updated


@pytest.mark.parametrize(
    "file_upload_state,bad_event_field,bad_event_value",
    [
        # Wrong states - FileUpload is not in 'awaiting_archival' or 'archived'
        ("init", None, None),
        ("inbox", None, None),
        ("interrogated", None, None),
        ("failed", None, None),
        ("cancelled", None, None),
        # Field mismatches - state is correct but event data doesn't match
        ("awaiting_archival", "decrypted_sha256", "wrong-sha256"),
        ("awaiting_archival", "encrypted_parts_md5", ["wrong-md5"]),
        ("awaiting_archival", "encrypted_parts_sha256", ["wrong-sha256"]),
        ("awaiting_archival", "storage_alias", "wrong-alias"),
        ("awaiting_archival", "secret_id", "wrong-secret"),
        ("awaiting_archival", "decrypted_size", DECRYPTED_SIZE + 1),
        ("awaiting_archival", "encrypted_size", ENCRYPTED_SIZE + 1),
    ],
)
async def test_handle_internal_file_registration_state_error(
    rig: JointRig,
    file_upload_state: FileUploadState,
    bad_event_field: str | None,
    bad_event_value,
):
    """Test that FileUploadStateError is raised when the FileUpload is in an unexpected
    state, or when any of the checked fields differ between the FileUpload and the event.
    """
    file_upload = make_file_upload(state="awaiting_archival")
    file_upload.state = file_upload_state
    await rig.file_upload_dao.insert(file_upload)

    event = _make_matching_event(file_upload)
    if bad_event_field is not None:
        event = event.model_copy(update={bad_event_field: bad_event_value})

    with pytest.raises(UploadControllerPort.FileUploadStateError):
        await rig.controller.process_internal_file_registration(
            registration_metadata=event
        )


async def test_upload_activity_lifecycle(rig: JointRig):
    """Test that an UploadActivity entry is created when a FileUpload is initiated
    and deleted when the upload is completed.
    """
    assert not [x async for x in rig.upload_activity_dao.find_all(mapping={})]
    box_id = await rig.create_default_box()
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test-file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Verify that UploadActivity and FileUpload exist
    activity = await rig.upload_activity_dao.get_by_id(file_id)
    assert activity.file_id == file_id

    file_upload = rig.file_upload_dao.latest
    assert file_upload.id == file_id

    # Complete the upload
    await rig.controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id,
        unencrypted_checksum="abc",
        encrypted_checksum=f"etag_for_{file_upload.object_id}",
        encrypted_parts_md5=["abc"],
        encrypted_parts_sha256=["def"],
    )

    # UploadActivity entry should be gone
    with pytest.raises(ResourceNotFoundError):
        await rig.upload_activity_dao.get_by_id(file_id)


async def test_upload_activity_deleted_on_abort(rig: JointRig):
    """Test that the UploadActivity entry is deleted when a FileUpload is aborted."""
    box_id = await rig.create_default_box()
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test-file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Make sure the upload activity is there
    await rig.upload_activity_dao.get_by_id(file_id)

    # Remove the file upload
    await rig.controller.remove_file_upload(box_id=box_id, file_id=file_id)

    # UploadActivity entry should be gone
    with pytest.raises(ResourceNotFoundError):
        await rig.upload_activity_dao.get_by_id(file_id)


async def test_cleanup_cancels_stale_file_upload(rig: JointRig):
    """Test that the cleanup job sets the FileUpload state to 'cancelled' when
    aborting a stale upload.
    """
    box_id = await rig.create_default_box()
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test-file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Backdate the activity entry so the upload appears stale (beyond the 72h TTL)
    stale_timestamp = now_utc_ms_prec() - timedelta(hours=73)
    await rig.upload_activity_dao.upsert(
        UploadActivity(file_id=file_id, last_activity=stale_timestamp)
    )

    # Run the cleanup job
    await rig.controller.cleanup_stale_uploads()

    # Verify the FileUpload state is set to "cancelled"
    file_upload = await rig.file_upload_dao.get_by_id(file_id)
    assert file_upload.state == "cancelled"

    # UploadActivity entry should be gone
    with pytest.raises(ResourceNotFoundError):
        await rig.upload_activity_dao.get_by_id(file_id)


async def test_cleanup_falls_back_to_initiated_when_no_activity(rig: JointRig):
    """Test that the cleanup job uses the FileUpload's initiated timestamp when no
    UploadActivity entry exists, and still cancels the upload if that timestamp is older
    than the cutoff allows.
    """
    file_upload = make_file_upload(state="init")
    file_upload.initiated = now_utc_ms_prec() - timedelta(hours=73)
    await rig.file_upload_dao.insert(file_upload)

    # No activity entry is created for this file
    assert not [x async for x in rig.upload_activity_dao.find_all(mapping={})]

    # Run the cleanup job and make sure the upload is still cancelled
    await rig.controller.cleanup_stale_uploads()
    refreshed = await rig.file_upload_dao.get_by_id(file_upload.id)
    assert refreshed.state == "cancelled"


async def test_cleanup_cancels_despite_s3_abort_failure(
    rig: JointRig, monkeypatch: pytest.MonkeyPatch
):
    """Test that the cleanup job marks a stale upload as 'cancelled' even when the
    S3 abort call raises an error.
    """
    box_id = await rig.create_default_box()
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test-file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    stale_timestamp = now_utc_ms_prec() - timedelta(hours=73)
    await rig.upload_activity_dao.upsert(
        UploadActivity(file_id=file_id, last_activity=stale_timestamp)
    )

    # Patch the abort_multipart_upload() method on the S3Client so it raises an error
    file_upload = rig.file_upload_dao.latest

    async def failing_abort(**kwargs):
        raise rig.s3_client.S3UploadAbortError(
            s3_upload_id=file_upload.s3_upload_id,
            object_id=str(file_upload.object_id),
            bucket_id=file_upload.bucket_id,
        )

    monkeypatch.setattr(rig.s3_client, "abort_multipart_upload", failing_abort)

    # Run the cleanup job
    await rig.controller.cleanup_stale_uploads()

    # Make sure that the file upload is marked cancelled and activity entry removed
    file_upload = await rig.file_upload_dao.get_by_id(file_id)
    assert file_upload.state == "cancelled"
    with pytest.raises(ResourceNotFoundError):
        await rig.upload_activity_dao.get_by_id(file_id)


async def test_activity_refresh_prevents_stale_cancellation(rig: JointRig):
    """Test that requesting a part URL refreshes the activity timestamp, preventing
    the upload from being treated as stale in a subsequent cleanup run.
    """
    box_id = await rig.create_default_box()
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test-file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Backdate the activity so that it WOULD get cleaned up if nothing intervened
    stale_timestamp = now_utc_ms_prec() - timedelta(hours=73)
    await rig.upload_activity_dao.upsert(
        UploadActivity(file_id=file_id, last_activity=stale_timestamp)
    )

    # Refresh the activity timestamp
    await rig.controller.refresh_upload_activity(file_id=file_id)

    # Verify the activity timestamp has been updated
    activity = await rig.upload_activity_dao.get_by_id(file_id)
    assert activity.last_activity > stale_timestamp

    # Run the cleanup job
    await rig.controller.cleanup_stale_uploads()

    # Verify the upload has not been cancelled
    file_upload = await rig.file_upload_dao.get_by_id(file_id)
    assert file_upload.state == "init"


async def test_orphaned_abort_failure_does_not_stop_cleanup(
    rig: JointRig, monkeypatch: pytest.MonkeyPatch
):
    """Test that a failure aborting one orphaned S3 upload does not prevent the cleanup
    job from attempting to abort the remaining orphaned uploads.
    """
    bucket_id, object_storage = rig.object_storages.for_alias("test")

    # Create two orphaned S3 multipart uploads (no corresponding FileUpload records)
    await object_storage.init_multipart_upload(
        bucket_id=bucket_id, object_id=str(uuid4())
    )
    await object_storage.init_multipart_upload(
        bucket_id=bucket_id, object_id=str(uuid4())
    )

    call_count = 0

    async def always_failing_abort(**kwargs):
        nonlocal call_count
        call_count += 1
        raise rig.s3_client.S3UploadAbortError(
            s3_upload_id="some_id", object_id="some_object", bucket_id="some_bucket"
        )

    monkeypatch.setattr(rig.s3_client, "abort_multipart_upload", always_failing_abort)

    await rig.controller.cleanup_stale_uploads()

    # Both orphaned uploads were attempted despite the first failure
    assert call_count == 2


async def test_refresh_activity_warns_and_recreates_when_missing(rig: JointRig):
    """Test that _refresh_upload_activity logs a warning and recreates the entry
    when the activity record is unexpectedly absent during a part URL request.
    """
    box_id = await rig.create_default_box()
    file_id, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test-file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Manually delete the upload activity entry
    await rig.upload_activity_dao.delete(file_id)

    # Manually fetch a presigned part upload URL, which should recreate the entry
    await rig.controller.refresh_upload_activity(file_id=file_id)
    await sleep(0)  # yield to let the background task run

    # Verify the entry now exists again
    activity = await rig.upload_activity_dao.get_by_id(file_id)
    assert activity.file_id == file_id


async def test_initiate_file_upload_marks_failed_on_insert_kafka_error(
    rig: JointRig,
    caplog: pytest.LogCaptureFixture,
):
    """If a Kafka publishing error occurs during the FileUpload insert (or some other
    kind of equivalent error), the FileUpload must be marked "failed" so that a
    subsequent retry can replace it.

    The test `test_initiate_upload_after_failed()` covers the process of starting a new
    upload for the same essential file after a FileUpload is "failed".
    """
    box_id = await rig.create_default_box()

    # Simulate the outbox publisher scenario: MongoDB write succeeds (we call the real
    # insert), then Kafka raises an error (the reason doesn't matter)
    original_insert = rig.file_upload_dao.insert
    original_upsert = rig.file_upload_dao.upsert

    async def insert_then_fail(dto):
        await original_insert(dto)
        raise RuntimeError("First Error")

    async def upsert_then_fail(dto):
        await original_upsert(dto)
        raise RuntimeError("Follow-up Error")

    rig.file_upload_dao.insert = insert_then_fail
    rig.file_upload_dao.upsert = upsert_then_fail

    with caplog.at_level(logging.INFO, logger="ucs.core.controller"):
        with pytest.raises(RuntimeError, match="First Error"):
            await rig.controller.initiate_file_upload(
                box_id=box_id,
                alias="test-file",
                decrypted_size=DECRYPTED_SIZE,
                encrypted_size=ENCRYPTED_SIZE,
                part_size=PART_SIZE,
            )

    controller_logs = [r for r in caplog.records if r.name == "ucs.core.controller"]
    error_logs = [r for r in controller_logs if r.levelno == logging.ERROR]
    warning_logs = [r for r in controller_logs if r.levelno == logging.WARNING]
    info_logs = [r for r in controller_logs if r.levelno == logging.INFO]

    assert len(error_logs) == 1
    assert (
        "Encountered an error while inserting FileUpload" in error_logs[0].getMessage()
    )

    assert len(warning_logs) == 1
    assert "While marking FileUpload" in warning_logs[0].getMessage()

    assert len(info_logs) == 1
    assert "as 'failed' due to error during initiation" in info_logs[0].getMessage()

    # The FileUpload was written to the DB but must now be marked 'failed'
    assert len(rig.file_upload_dao.resources) == 1
    stuck_upload = rig.file_upload_dao.latest
    assert stuck_upload.state == "failed"
    assert stuck_upload.failure_reason == "Internal error during upload initiation"

    # Just double check that no UploadActivity was inserted
    assert not [x async for x in rig.upload_activity_dao.find_all(mapping={})]


@pytest.mark.parametrize("box_state", ["open", "locked"])
async def test_remove_file_upload_box_open_and_locked(rig: JointRig, box_state: str):
    """Test that a box in 'open' or 'locked' state can be successfully deleted."""
    box_id = await rig.create_default_box()
    if box_state == "locked":
        await rig.controller.lock_file_upload_box(box_id=box_id, version=0)

    await rig.controller.remove_file_upload_box(box_id=box_id)

    assert not rig.file_upload_box_dao.resources


async def test_remove_file_upload_box_version_check(rig: JointRig):
    """Test that supplying an outdated version raises BoxVersionError and leaves the
    box intact, while supplying the current version allows deletion.
    """
    box_id = await rig.create_default_box()

    with pytest.raises(UploadControllerPort.BoxVersionError) as exc_info:
        await rig.controller.remove_file_upload_box(box_id=box_id, version=99)

    assert str(box_id) in str(exc_info.value)
    assert rig.file_upload_box_dao.resources

    await rig.controller.remove_file_upload_box(box_id=box_id, version=0)
    assert not rig.file_upload_box_dao.resources


async def test_remove_file_upload_box_when_archived(rig: JointRig):
    """Test that BoxStateError is raised when attempting to delete an archived box."""
    box_id = await rig.create_default_box()
    box = await rig.file_upload_box_dao.get_by_id(box_id)
    box.state = "archived"
    await rig.file_upload_box_dao.update(box)

    with pytest.raises(UploadControllerPort.BoxStateError) as exc_info:
        await rig.controller.remove_file_upload_box(box_id=box_id)

    assert str(box_id) in str(exc_info.value)
    assert rig.file_upload_box_dao.resources


async def test_remove_file_upload_box_not_found(rig: JointRig):
    """Test that BoxNotFoundError is raised for a non-existent box ID."""
    non_existent_box_id = uuid4()

    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await rig.controller.remove_file_upload_box(box_id=non_existent_box_id)

    assert str(non_existent_box_id) in str(exc_info.value)


@pytest.mark.parametrize("bad_state", ["awaiting_archival", "archived"])
async def test_remove_file_upload_box_with_invalid_file_state(
    rig: JointRig, bad_state: FileUploadState
):
    """Test that FileUploadStateError is raised when a FileUpload is in 'awaiting_archival'
    or 'archived' state, which indicates a data inconsistency.
    """
    box_id = await rig.create_default_box()
    file_upload = make_file_upload(state=bad_state)
    file_upload.box_id = box_id
    await rig.file_upload_dao.insert(file_upload)

    with pytest.raises(UploadControllerPort.FileUploadStateError) as exc_info:
        await rig.controller.remove_file_upload_box(box_id=box_id)

    assert str(file_upload.id) in str(exc_info.value)
    assert rig.file_upload_box_dao.resources


async def test_remove_file_upload_box_success(
    rig: JointRig, monkeypatch: pytest.MonkeyPatch
):
    """Test that removing a box correctly handles each FileUpload state:
    - 'init': S3 multipart upload is aborted
    - 'inbox': S3 object is deleted
    - 'interrogated', 'failed', 'cancelled': no S3 action

    The box and all its FileUploads are hard-deleted from the DB and the activity
    entry for the init file is removed as well.
    """
    box_id = await rig.create_default_box()
    storage_alias = next(iter(rig.config.object_storages))

    s3_calls: list[str] = []

    async def spy_delete_inbox_file(**kwargs):
        s3_calls.append("delete_inbox_file")

    async def spy_abort_multipart_upload(**kwargs):
        s3_calls.append("abort_multipart_upload")

    monkeypatch.setattr(rig.s3_client, "delete_inbox_file", spy_delete_inbox_file)
    monkeypatch.setattr(
        rig.s3_client, "abort_multipart_upload", spy_abort_multipart_upload
    )

    file_uploads_by_state: dict[str, FileUpload] = {}
    for state in ["init", "inbox", "interrogated", "failed", "cancelled"]:
        file_upload = make_file_upload(state=state, storage_alias=storage_alias)
        file_upload.box_id = box_id
        await rig.file_upload_dao.insert(file_upload)
        file_uploads_by_state[state] = file_upload

    init_file = file_uploads_by_state["init"]
    await rig.upload_activity_dao.upsert(
        UploadActivity(file_id=init_file.id, last_activity=now_utc_ms_prec())
    )

    # Call the box deletion method
    await rig.controller.remove_file_upload_box(box_id=box_id)

    # Verify the box is gone
    assert not rig.file_upload_box_dao.resources

    # Should have one file deletion due to 'inbox' and one upload abort due to 'init'
    assert s3_calls.count("abort_multipart_upload") == 1
    assert s3_calls.count("delete_inbox_file") == 1

    # Verify that all FileUploads were hard-deleted regardless of state
    assert not rig.file_upload_dao.resources

    # Make sure the upload activity associated with the 'init' file is deleted
    with pytest.raises(ResourceNotFoundError):
        await rig.upload_activity_dao.get_by_id(init_file.id)


async def test_remove_file_upload_box_s3_abort_error(rig: JointRig):
    """Make sure an UploadAbortError is raised and the box is NOT deleted when S3 fails
    to abort a multipart upload for an 'init'-state file. The box is left locked
    because deletion locks open boxes before sweeping their uploads.
    """
    box_id = await rig.create_default_box()

    # Make an upload, we don't care about the file ID or upload ID
    _, _ = await rig.controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Hardwire the object storage to raise an error when we try to abort the upload
    storage = rig.object_storages.for_alias("test")[1]

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadAbortError("", "", "")

    storage.abort_multipart_upload = do_error

    # Call the box deletion method
    with pytest.raises(UploadControllerPort.UploadAbortError):
        await rig.controller.remove_file_upload_box(box_id=box_id)

    # Verify that the box is still there and still locked
    assert rig.file_upload_box_dao.resources
    surviving_box = await rig.file_upload_box_dao.get_by_id(box_id)
    assert surviving_box.state == "locked"
