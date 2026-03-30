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

"""Tests for the UploadController class"""

from asyncio import sleep
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from ghga_event_schemas.pydantic_ import (
    FileInternallyRegistered,
    FileUploadState,
    InterrogationSuccess,
)
from hexkit.protocols.dao import UniqueConstraintViolationError
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.utils import now_utc_ms_prec

from tests_ucs.fixtures.joint import JointRig
from tests_ucs.fixtures.utils import (
    DECRYPTED_SIZE,
    ENCRYPTED_SIZE,
    PART_SIZE,
    make_file_upload,
)
from ucs.core.models import FileUpload
from ucs.ports.inbound.controller import UploadControllerPort

pytestmark = pytest.mark.asyncio()


@pytest_asyncio.fixture(autouse=True)
async def create_default_bucket(rig: JointRig):
    """Create the `test-inbox` bucket automatically for tests."""
    await rig.object_storages.for_alias("test")[1].create_bucket("test-inbox")


async def test_create_new_box(rig: JointRig):
    """Test creating a new FileUploadBox"""
    box_id = await rig.controller.create_file_upload_box(storage_alias="test")
    assert rig.file_upload_box_dao.latest.id == box_id
    assert rig.file_upload_box_dao.latest.version == 0
    assert rig.file_upload_box_dao.latest.state == "open"


async def test_create_new_file_upload(rig: JointRig):
    """Test creating a new FileUpload"""
    # First create a FileUploadBox
    file_upload_dao = rig.file_upload_dao
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Then create a FileUpload within the box
    file_id, _ = await controller.initiate_file_upload(
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
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Then create a FileUpload within the box
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )

    # Now get the part upload URL
    part_no = 1
    result_url = await controller.get_part_upload_url(file_id=file_id, part_no=part_no)

    # Verify the URL was returned
    assert result_url.startswith("https://s3.example.com/")


async def test_complete_file_upload(rig: JointRig):
    """Test completing a multipart file upload"""
    # First create a FileUploadBox
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Then create a FileUpload within the box
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
    assert file_upload_dao.latest.inbox_upload_completed
    file_upload_box_dao = rig.file_upload_box_dao
    assert file_upload_box_dao.latest.size == DECRYPTED_SIZE
    assert file_upload_box_dao.latest.file_count == 1

    # Now repeat the process to ensure the box stats are incremented, not overwritten
    await sleep(0.1)
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
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao
    bucket_id, object_storage = rig.object_storages.for_alias("test")

    # First create a FileUploadBox
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Then create a FileUpload within the box
    file_id, _ = await controller.initiate_file_upload(
        box_id=box_id,
        alias="test_file",
        decrypted_size=DECRYPTED_SIZE,
        encrypted_size=ENCRYPTED_SIZE,
        part_size=PART_SIZE,
    )
    object_id = str(rig.file_upload_dao.latest.object_id)

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

    # FileUpload is set to "cancelled" (not removed from DB)
    assert len(file_upload_dao.resources) == 1
    assert file_upload_dao.latest.state == "cancelled"
    assert file_upload_box_dao.latest.file_count == 0
    assert file_upload_box_dao.latest.size == 0


async def test_lock_file_upload_box(rig: JointRig):
    """Test locking an unlocked FileUploadBox"""
    # First create a FileUploadBox (starts open by default)
    file_upload_box_dao = rig.file_upload_box_dao
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Verify the box starts open
    assert file_upload_box_dao.latest.state == "open"

    # Now lock the box
    await controller.lock_file_upload_box(box_id=box_id, version=0)

    # Verify the box is now locked
    assert file_upload_box_dao.latest.state == "locked"


async def test_unlock_file_upload_box(rig: JointRig):
    """Test unlocking a locked FileUploadBox"""
    file_upload_box_dao = rig.file_upload_box_dao
    controller = rig.controller

    # First create a FileUploadBox
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Lock the box first (version 0 → 1)
    await controller.lock_file_upload_box(box_id=box_id, version=0)
    assert file_upload_box_dao.latest.state == "locked"

    # Now unlock the box (version 1 → 2)
    await controller.unlock_file_upload_box(box_id=box_id, version=1)

    # Verify the box is now unlocked
    assert file_upload_box_dao.latest.state == "open"


async def test_lock_box_version_error(rig: JointRig):
    """Test that BoxVersionError is raised when the wrong version is supplied for lock."""
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    with pytest.raises(UploadControllerPort.BoxVersionError) as exc_info:
        await controller.lock_file_upload_box(box_id=box_id, version=99)

    assert str(box_id) in str(exc_info.value)
    # Box should remain unlocked
    assert rig.file_upload_box_dao.latest.state == "open"


async def test_unlock_box_version_error(rig: JointRig):
    """Test that BoxVersionError is raised when the wrong version is supplied for unlock."""
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")
    await controller.lock_file_upload_box(box_id=box_id, version=0)

    with pytest.raises(UploadControllerPort.BoxVersionError) as exc_info:
        await controller.unlock_file_upload_box(box_id=box_id, version=0)

    assert str(box_id) in str(exc_info.value)
    # Box should remain locked
    assert rig.file_upload_box_dao.latest.state == "locked"


async def test_get_box_uploads(rig: JointRig):
    """Test getting file IDs for a given box ID"""
    controller = rig.controller

    # First create a FileUploadBox
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Create multiple FileUploads within the box and complete them
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
    other_box_id = await controller.create_file_upload_box(storage_alias="test")
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
    empty_box_id = await controller.create_file_upload_box(storage_alias="test")

    # Get the file uploads for the first box - should be sorted by alias
    results = await controller.get_box_file_info(box_id=box_id)
    assert len(results) == 3
    assert [r.alias for r in results] == ["file0", "file1", "file2"]
    assert all(r.id in file_ids for r in results)

    # Verify the other box returns only its own files
    other_results = await controller.get_box_file_info(box_id=other_box_id)
    assert len(other_results) == 2
    assert all(r.id in other_file_ids for r in other_results)

    # Verify that we get an empty list for the third box
    no_ids = await controller.get_box_file_info(box_id=empty_box_id)
    assert no_ids == []


async def test_create_box_with_unknown_storage_alias(rig: JointRig):
    """Test for error handling when the user tries to create new FileUploadBox
    with a storage alias that isn't configured.
    """
    # Try to create a FileUploadBox with an unknown storage alias
    controller = rig.controller
    unknown_storage_alias = "unknown_storage_alias_that_does_not_exist"

    # Should raise UnknownStorageAliasError
    with pytest.raises(UploadControllerPort.UnknownStorageAliasError) as exc_info:
        await controller.create_file_upload_box(storage_alias=unknown_storage_alias)

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
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao

    # First create a FileUploadBox and lock it (version 0 → 1)
    box_id = await controller.create_file_upload_box(storage_alias="test")
    await controller.lock_file_upload_box(box_id=box_id, version=0)
    assert file_upload_box_dao.latest.state == "locked"

    # Try to create a FileUpload in the locked box - should raise BoxStateError
    with pytest.raises(UploadControllerPort.BoxStateError) as exc_info:
        await controller.initiate_file_upload(
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
    box_id = await controller.create_file_upload_box(storage_alias="test")
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


async def test_delete_file_upload_when_upload_missing(rig: JointRig):
    """Test error handling in the case where the user tries to delete a FileUpload
    that doesn't exist.
    """
    controller = rig.controller

    # Create a FileUploadBox
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Try to delete a FileUpload that doesn't exist - this should NOT raise an error
    await controller.remove_file_upload(box_id=box_id, file_id=uuid4())


async def test_delete_file_upload_with_s3_error(rig: JointRig):
    """Test for error handling when the user tries to delete a FileUpload
    but gets an S3 error in the process of aborting an ongoing upload.
    """
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
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
    box_id = await controller.create_file_upload_box(storage_alias="test")

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
    file_ids = sorted([file_id1, file_id2])

    # Attempt to lock the box while the upload is still incomplete
    with pytest.raises(UploadControllerPort.IncompleteUploadsError) as exc_info:
        await controller.lock_file_upload_box(box_id=box_id, version=0)

    # Verify the exception is correct
    assert (
        str(exc_info.value)
        == f"Cannot lock or archive box {box_id} because these files are incomplete: {file_ids}"
    )

    # Verify that the box is still open
    assert file_upload_box_dao.latest.state == "open"


async def test_complete_file_upload_when_box_missing(rig: JointRig):
    """Test error handling in the case where the user tries to complete a FileUpload
    for a box ID that doesn't exist.
    """
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao

    # Create a FileUploadBox and a FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id, _ = await controller.initiate_file_upload(
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
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum="sha256:encrypted_checksum_here",
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    # Verify the exception contains the correct box_id
    assert str(box_id) in str(exc_info.value)
    assert not file_upload_dao.latest.inbox_upload_completed


async def test_complete_missing_file_upload(rig: JointRig):
    """Test error handling in the case where the user tries to complete a FileUpload
    that doesn't exist.
    """
    # Create a box first
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Try to complete a file upload that doesn't exist
    non_existent_file_id = uuid4()

    with pytest.raises(UploadControllerPort.FileUploadNotFound) as exc_info:
        await controller.complete_file_upload(
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
    box_id = await controller.create_file_upload_box(storage_alias="test")
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
    assert not file_upload_dao.latest.inbox_upload_completed
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
    box_id = await controller.create_file_upload_box(storage_alias="test")
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
    assert not rig.file_upload_dao.latest.inbox_upload_completed
    assert not file_upload_dao.latest.completed
    assert file_upload_box_dao.latest.size == 0
    assert file_upload_box_dao.latest.file_count == 0


async def test_complete_file_upload_checksum_mismatch(rig: JointRig):
    """Test to make sure the FileUpload is marked as 'failed' if the UploadController
    raises a ChecksumMismatchError.
    """
    file_upload_box_dao = rig.file_upload_box_dao
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
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

    await sleep(0.1)  # short sleep for differentiating timestamps

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
    assert not file_upload.inbox_upload_completed
    assert not file_upload.completed
    assert file_upload_box_dao.latest.size == 0
    assert file_upload_box_dao.latest.file_count == 0


async def test_get_part_upload_url_with_unknown_storage_alias(rig: JointRig):
    """Test for error handling when getting a part URL but the storage alias found in
    the FileUpload is unknown (maybe configuration changed or data was migrated wrong).
    """
    # Create a FileUploadBox and a FileUpload with a valid storage alias
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")
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
    box_id = await controller.create_file_upload_box(storage_alias="test")
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

    box_id = await controller.create_file_upload_box(storage_alias="test")
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

    box_id = await controller.create_file_upload_box(storage_alias="test")
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

    box_id = await controller.create_file_upload_box(storage_alias="test")
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

    await sleep(0.1)  # sleep so that timestamp comparisons are valid
    await rig.controller.process_internal_file_registration(registration_metadata=event)
    updated_file_upload = await rig.file_upload_dao.get_by_id(file_upload.id)
    assert updated_file_upload.state == "archived"
    assert updated_file_upload.state_updated > file_upload.state_updated

    # Now reprocess the event - should get no errors and timestamp should be unchanged
    await sleep(0.1)  # sleep so that timestamp comparisons are valid
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
