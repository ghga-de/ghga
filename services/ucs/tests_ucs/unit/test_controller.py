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
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from ghga_event_schemas.pydantic_ import (
    FileUpload,
    FileUploadBox,
    FileUploadReport,
    FileUploadState,
)
from ghga_service_commons.utils.multinode_storage import ObjectStorages
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.providers.testing.s3 import InMemObjectStorage
from hexkit.utils import now_utc_ms_prec

from tests_ucs.fixtures import ConfigFixture
from tests_ucs.fixtures.in_mem_dao import (
    BaseInMemDao,
    InMemFileUploadBoxDao,
    InMemFileUploadDao,
    InMemS3UploadDetailsDao,
)
from tests_ucs.fixtures.in_mem_obj_storage import (
    InMemS3ObjectStorages,
    raise_object_storage_error,
)
from ucs.config import Config
from ucs.core import models
from ucs.core.controller import UploadController
from ucs.ports.inbound.controller import UploadControllerPort

pytestmark = pytest.mark.asyncio()


@pytest.fixture()
def patch_s3_calls(monkeypatch):
    """Mocks the object storage provider with an InMemObjectStorage object"""
    pass
    monkeypatch.setattr(
        f"{InMemS3ObjectStorages.__module__}.S3ObjectStorage", InMemObjectStorage
    )


@dataclass
class JointRig:
    """Test fixture containing all components needed for controller testing."""

    config: Config
    file_upload_box_dao: BaseInMemDao[FileUploadBox]
    file_upload_dao: BaseInMemDao[FileUpload]
    s3_upload_details_dao: BaseInMemDao[models.S3UploadDetails]
    object_storages: ObjectStorages
    controller: UploadController


@pytest.fixture()
def rig(config: ConfigFixture, patch_s3_calls) -> JointRig:
    """Return a joint fixture with in-memory dependency mocks"""
    controller = UploadController(
        config=(_config := config.config),
        file_upload_box_dao=(file_upload_box_dao := InMemFileUploadBoxDao()),
        file_upload_dao=(file_upload_dao := InMemFileUploadDao()),
        s3_upload_details_dao=(s3_upload_details_dao := InMemS3UploadDetailsDao()),
        object_storages=(object_storages := InMemS3ObjectStorages(config=_config)),
    )

    return JointRig(
        config=_config,
        file_upload_box_dao=file_upload_box_dao,
        file_upload_dao=file_upload_dao,
        s3_upload_details_dao=s3_upload_details_dao,
        object_storages=object_storages,
        controller=controller,
    )


@pytest_asyncio.fixture(autouse=True)
async def create_default_bucket(rig: JointRig):
    """Create the `test-inbox` bucket automatically for tests."""
    await rig.object_storages.for_alias("test")[1].create_bucket("test-inbox")


async def test_create_new_box(rig: JointRig):
    """Test creating a new FileUploadBox"""
    box_id = await rig.controller.create_file_upload_box(storage_alias="test")
    assert rig.file_upload_box_dao.latest.id == box_id


async def test_create_new_file_upload(rig: JointRig):
    """Test creating a new FileUpload"""
    # First create a FileUploadBox
    file_upload_dao = rig.file_upload_dao
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Then create a FileUpload within the box
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Verify the FileUpload was created
    assert file_upload_dao.latest.id == file_id
    assert file_upload_dao.latest.alias == "test_file"
    assert file_upload_dao.latest.checksum == ""
    assert file_upload_dao.latest.size == 1024

    # Verify S3UploadDetails were created
    upload_details = rig.s3_upload_details_dao.latest
    assert upload_details.file_id == file_id
    assert upload_details.storage_alias == "test"
    assert now_utc_ms_prec() - upload_details.initiated < timedelta(seconds=5)
    assert not upload_details.completed


async def test_get_part_url(rig: JointRig):
    """Test getting a file part upload URL"""
    # First create a FileUploadBox
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Then create a FileUpload within the box
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
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
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Now complete the file upload
    await controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{file_id}",
    )
    bucket_id, object_storage = rig.object_storages.for_alias("test")
    assert await object_storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file_id)
    )

    # Verify that the S3UploadDetails still exist (they should remain for tracking)
    completed = now_utc_ms_prec()
    s3_upload_details_dao = rig.s3_upload_details_dao
    assert s3_upload_details_dao.latest.file_id == file_id
    assert s3_upload_details_dao.latest.completed is not None
    assert completed - s3_upload_details_dao.latest.completed < timedelta(seconds=5)
    assert rig.file_upload_dao.latest.completed
    file_upload_box_dao = rig.file_upload_box_dao
    assert file_upload_box_dao.latest.size == 1024
    assert file_upload_box_dao.latest.file_count == 1

    # Now repeat the process to ensure the box stats are incremented, not overwritten
    await sleep(0.1)
    file_id2 = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file2", size=1000
    )
    await controller.complete_file_upload(
        box_id=box_id,
        file_id=file_id2,
        unencrypted_checksum="unencrypted_checksum",
        encrypted_checksum=f"etag_for_{file_id2}",
    )
    latest_s3_details = s3_upload_details_dao.latest
    assert latest_s3_details.file_id == file_id2
    assert latest_s3_details.completed
    assert latest_s3_details.completed > completed
    assert file_upload_box_dao.latest.file_count == 2
    assert file_upload_box_dao.latest.size == 2024


@pytest.mark.parametrize("complete_before_delete", [True, False])
async def test_delete_file_upload(rig: JointRig, complete_before_delete: bool):
    """Test deleting a FileUpload from a FileUploadBox"""
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao
    s3_upload_details_dao = rig.s3_upload_details_dao
    bucket_id, object_storage = rig.object_storages.for_alias("test")

    # First create a FileUploadBox
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Then create a FileUpload within the box
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    if complete_before_delete:
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="unencrypted_checksum",
            encrypted_checksum=f"etag_for_{file_id}",
        )
        assert file_upload_box_dao.latest.file_count == 1
        assert file_upload_box_dao.latest.size == 1024
        assert await object_storage.does_object_exist(
            bucket_id=bucket_id, object_id=str(file_id)
        )

    # Now delete the file upload
    await controller.remove_file_upload(box_id=box_id, file_id=file_id)
    assert not await object_storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file_id)
    )

    # Verify that the FileUpload and S3UploadDetails were removed
    assert not file_upload_dao.resources
    assert not s3_upload_details_dao.resources
    assert file_upload_box_dao.latest.file_count == 0
    assert file_upload_box_dao.latest.size == 0


async def test_lock_file_upload_box(rig: JointRig):
    """Test locking an unlocked FileUploadBox"""
    # First create a FileUploadBox (starts unlocked by default)
    file_upload_box_dao = rig.file_upload_box_dao
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Verify the box starts unlocked
    assert not file_upload_box_dao.latest.locked

    # Now lock the box
    await controller.lock_file_upload_box(box_id=box_id)

    # Verify the box is now locked
    assert file_upload_box_dao.latest.locked


async def test_unlock_file_upload_box(rig: JointRig):
    """Test unlocking a locked FileUploadBox"""
    file_upload_box_dao = rig.file_upload_box_dao
    controller = rig.controller

    # First create a FileUploadBox
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Lock the box first
    await controller.lock_file_upload_box(box_id=box_id)
    assert file_upload_box_dao.latest.locked

    # Now unlock the box
    await controller.unlock_file_upload_box(box_id=box_id)

    # Verify the box is now unlocked
    assert not file_upload_box_dao.latest.locked


async def test_get_box_uploads(rig: JointRig):
    """Test getting file IDs for a given box ID"""
    controller = rig.controller

    # First create a FileUploadBox
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Create multiple FileUploads within the box
    file_uploads: list[FileUpload] = []
    for i in range(3):
        file_id = await controller.initiate_file_upload(
            box_id=box_id,
            alias=f"file{i}",
            size=1024,
        )
        file_upload = FileUpload(
            id=file_id,
            box_id=box_id,
            state=FileUploadState.INBOX,
            alias=f"file{i}",
            size=1024,
            checksum="unencrypted_checksum",
            completed=True,
        )
        file_uploads.append(file_upload)

    # Create a second box with different files to test isolation
    other_box_id = await controller.create_file_upload_box(storage_alias="test")
    other_file_uploads: list[FileUpload] = []
    for i in range(2):
        other_file_id = await controller.initiate_file_upload(
            box_id=other_box_id,
            alias=f"file{i}",
            size=1024,
        )
        file_upload = FileUpload(
            id=other_file_id,
            box_id=other_box_id,
            state=FileUploadState.INBOX,
            alias=f"file{i}",
            size=1024,
            checksum="unencrypted_checksum",
            completed=True,
        )
        other_file_uploads.append(file_upload)

    # Complete the file uploads so they appear in the results
    for file_upload in file_uploads:
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_upload.id,
            unencrypted_checksum="unencrypted_checksum",
            encrypted_checksum=f"etag_for_{file_upload.id}",
        )

    # Complete the uploads in the other box too
    for file_upload in other_file_uploads:
        await controller.complete_file_upload(
            box_id=other_box_id,
            file_id=file_upload.id,
            unencrypted_checksum="unencrypted_checksum",
            encrypted_checksum=f"etag_for_{file_upload.id}",
        )

    # Create a third, empty box
    empty_box_id = await controller.create_file_upload_box(storage_alias="test")

    # Get the file uploads for the first box
    results = await controller.get_box_file_info(box_id=box_id)

    # Verify only the files from the first box are returned (not from other_box)
    expected_file_uploads = [file_uploads[0], file_uploads[1], file_uploads[2]]
    assert str(results) == str(expected_file_uploads)

    # Also verify the other box returns its own files
    other_results = await controller.get_box_file_info(box_id=other_box_id)
    expected_other_file_uploads = [other_results[0], other_results[1]]
    assert str(other_results) == str(expected_other_file_uploads)

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
            size=1024,
        )

    # Verify the exception contains the correct box_id
    assert str(non_existent_box_id) in str(exc_info.value)

    # Verify no FileUpload was created
    assert not rig.file_upload_dao.resources
    assert not rig.s3_upload_details_dao.resources


async def test_create_file_upload_when_box_locked(rig: JointRig):
    """Test error handling in the case where the user tries to create a FileUpload
    in a locked FileUploadBox.
    """
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao

    # First create a FileUploadBox and lock it
    box_id = await controller.create_file_upload_box(storage_alias="test")
    await controller.lock_file_upload_box(box_id=box_id)
    assert file_upload_box_dao.latest.locked

    # Try to create a FileUpload in the locked box - should raise LockedBoxError
    with pytest.raises(UploadControllerPort.LockedBoxError) as exc_info:
        await controller.initiate_file_upload(
            box_id=box_id, alias="test_file", size=1024
        )

    # Verify the exception contains the correct box_id
    assert str(box_id) in str(exc_info.value)

    # Verify no FileUpload was created
    assert not rig.file_upload_dao.resources
    assert not rig.s3_upload_details_dao.resources


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
    assert not rig.s3_upload_details_dao.resources


async def test_delete_file_upload_when_box_locked(rig: JointRig):
    """Test error handling in the case where the user tries to delete a FileUpload
    in a locked FileUploadBox.
    """
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao
    s3_upload_details_dao = rig.s3_upload_details_dao

    # First create a FileUploadBox and FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Lock the box manually
    box = await file_upload_box_dao.get_by_id(box_id)
    box.locked = True
    await file_upload_box_dao.update(box)
    assert file_upload_box_dao.latest.locked

    # Try to delete the FileUpload from the locked box - should raise LockedBoxError
    with pytest.raises(UploadControllerPort.LockedBoxError) as exc_info:
        await controller.remove_file_upload(box_id=box_id, file_id=file_id)

    # Verify the exception contains the correct box_id
    assert str(box_id) in str(exc_info.value)

    # Verify the FileUpload and S3UploadDetails still exist (weren't deleted)
    assert len(file_upload_dao.resources) == 1
    assert len(s3_upload_details_dao.resources) == 1


async def test_delete_file_upload_when_upload_missing(rig: JointRig):
    """Test error handling in the case where the user tries to delete a FileUpload
    that doesn't exist.
    """
    controller = rig.controller

    # Create a FileUploadBox
    box_id = await controller.create_file_upload_box(storage_alias="test")

    # Try to delete a FileUpload that doesn't exist - this should NOT raise an error
    await controller.remove_file_upload(box_id=box_id, file_id=uuid4())


async def test_delete_file_upload_with_missing_s3_details(rig: JointRig):
    """Test error handling in the case where the user tries to delete a FileUpload
    where the s3 upload details are missing. This would be an unusual case,
    but we're still testing it.
    """
    controller = rig.controller
    file_upload_dao = rig.file_upload_dao
    s3_upload_details_dao = rig.s3_upload_details_dao

    # Create a FileUploadBox and a FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Verify both FileUpload and S3UploadDetails were created
    assert len(file_upload_dao.resources) == 1
    assert len(s3_upload_details_dao.resources) == 1

    # Manually delete the S3UploadDetails but leave the FileUpload
    # This simulates a data inconsistency where S3 details are missing
    await s3_upload_details_dao.delete(file_id)

    # Verify the FileUpload exists but S3UploadDetails are gone
    assert len(file_upload_dao.resources) == 1
    assert len(s3_upload_details_dao.resources) == 0

    # Try to delete the file upload - should raise S3UploadDetailsNotFoundError
    with pytest.raises(UploadControllerPort.S3UploadDetailsNotFoundError) as exc_info:
        await controller.remove_file_upload(box_id=box_id, file_id=file_id)

    # Verify the exception contains the correct file_id
    assert str(file_id) in str(exc_info.value)

    # Verify the FileUpload still exists (deletion was aborted due to missing S3 details)
    assert len(file_upload_dao.resources) == 1


async def test_delete_file_upload_with_s3_error(rig: JointRig):
    """Test for error handling when the user tries to delete a FileUpload
    but gets an S3 error in the process of aborting an ongoing upload.
    """
    controller = rig.controller
    s3_upload_details_dao = rig.s3_upload_details_dao

    # Create a FileUploadBox and a FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Set the mock to raise a MultiPartUploadAbortError
    # This simulates S3 failing to abort the multipart upload
    # Try to delete the file upload - should raise UploadAbortError
    storage = rig.object_storages.for_alias("test")[1]

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadAbortError("", "", "")

    storage.abort_multipart_upload = do_error  # type: ignore[method-assign]
    with (
        raise_object_storage_error(InMemObjectStorage.MultiPartUploadAbortError),
        pytest.raises(UploadControllerPort.UploadAbortError) as exc_info,
    ):
        await controller.remove_file_upload(box_id=box_id, file_id=file_id)

    # Verify the exception contains the S3 upload ID
    s3_upload_id = s3_upload_details_dao.latest.s3_upload_id
    assert s3_upload_id in str(exc_info.value)

    # Verify the FileUpload and S3UploadDetails still exist (deletion failed)
    assert len(rig.file_upload_dao.resources) == 1
    assert len(s3_upload_details_dao.resources) == 1


async def test_unlock_missing_box(rig: JointRig):
    """Test error handling for case where the user tries to unlock a missing box."""
    controller = rig.controller

    # Try to unlock a non-existent box
    non_existent_box_id = uuid4()
    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await controller.unlock_file_upload_box(box_id=non_existent_box_id)

    # Verify the exception contains the correct box_id
    assert str(non_existent_box_id) in str(exc_info.value)


async def test_lock_missing_box(rig: JointRig):
    """Test error handling for case where the user tries to lock a missing box."""
    controller = rig.controller

    # Try to lock a non-existent box
    non_existent_box_id = uuid4()

    # Should raise BoxNotFoundError
    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await controller.lock_file_upload_box(box_id=non_existent_box_id)

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

    file_id1 = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )
    file_id2 = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file2", size=1024
    )
    file_ids = sorted([file_id1, file_id2])

    # Attempt to lock the box while the upload is still incomplete
    with pytest.raises(UploadControllerPort.IncompleteUploadsError) as exc_info:
        await controller.lock_file_upload_box(box_id=box_id)

    # Verify the exception is correct
    assert (
        str(exc_info.value)
        == f"Cannot lock box {box_id} because these files are incomplete: {file_ids}"
    )

    # Verify that the box is still unlocked
    assert not file_upload_box_dao.latest.locked


async def test_complete_file_upload_when_box_missing(rig: JointRig):
    """Test error handling in the case where the user tries to complete a FileUpload
    for a box ID that doesn't exist.
    """
    controller = rig.controller
    file_upload_box_dao = rig.file_upload_box_dao
    file_upload_dao = rig.file_upload_dao
    s3_upload_details_dao = rig.s3_upload_details_dao

    # Create a FileUploadBox and a FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Manually delete the box (simulating a scenario where the box was deleted
    # but the file upload and S3 details remain orphaned)
    await file_upload_box_dao.delete(box_id)

    # Verify the box is gone but file upload and S3 details remain
    assert not file_upload_box_dao.resources
    assert len(file_upload_dao.resources) == 1
    assert len(s3_upload_details_dao.resources) == 1

    # Try to complete the file upload for the now missing box
    with pytest.raises(UploadControllerPort.BoxNotFoundError) as exc_info:
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum="sha256:encrypted_checksum_here",
        )

    # Verify the exception contains the correct box_id
    assert str(box_id) in str(exc_info.value)
    assert not file_upload_dao.latest.completed
    assert not s3_upload_details_dao.latest.completed


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
        )
    assert not rig.file_upload_dao.resources
    assert not rig.s3_upload_details_dao.resources

    # Verify the exception contains the correct file_id
    assert str(non_existent_file_id) in str(exc_info.value)


async def test_complete_file_upload_with_missing_s3_details(rig: JointRig):
    """Test error handling in the case where the user tries to complete a FileUpload
    where the s3 upload details are missing. This would be an unusual case,
    but we're still testing it.
    """
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Manually delete the S3UploadDetails but leave the FileUpload
    # This simulates a data inconsistency where S3 details are missing
    await rig.s3_upload_details_dao.delete(file_id)

    # Try to complete the file upload - should raise S3UploadDetailsNotFoundError
    with pytest.raises(UploadControllerPort.S3UploadDetailsNotFoundError) as exc_info:
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum="sha256:encrypted_checksum_here",
        )

    # Verify the exception contains the correct file_id
    assert str(file_id) in str(exc_info.value)

    # Verify the FileUpload is still marked as incomplete
    assert not rig.file_upload_dao.latest.completed
    assert rig.file_upload_box_dao.latest.size == 0
    assert rig.file_upload_box_dao.latest.file_count == 0


async def test_complete_file_upload_with_unknown_storage_alias(rig: JointRig):
    """Test for error handling when the user tries to complete a FileUpload
    with a storage alias that isn't configured.
    """
    file_upload_dao = rig.file_upload_dao
    s3_upload_details_dao = rig.s3_upload_details_dao
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload with a valid storage alias
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Verify both FileUpload and S3UploadDetails were created
    assert len(file_upload_dao.resources) == 1
    assert len(s3_upload_details_dao.resources) == 1

    # Manually modify the S3UploadDetails to have an unknown storage alias
    # This simulates a scenario where configuration changed or data was corrupted
    s3_details = s3_upload_details_dao.latest
    s3_details.storage_alias = "does_not_exist"
    await s3_upload_details_dao.update(s3_details)

    # Try to complete the file upload - should raise UnknownStorageAliasError
    with pytest.raises(UploadControllerPort.UnknownStorageAliasError) as exc_info:
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum="sha256:encrypted_checksum_here",
        )

    # Verify the exception message contains the unknown storage alias
    assert "does_not_exist" in str(exc_info.value)
    assert not file_upload_dao.latest.completed
    assert rig.file_upload_box_dao.latest.size == 0
    assert rig.file_upload_box_dao.latest.file_count == 0


async def test_complete_file_upload_with_s3_error(rig: JointRig):
    """Test for error handling when the user tries to complete a FileUpload
    but gets an S3 error in the process.
    """
    file_upload_box_dao = rig.file_upload_box_dao
    s3_upload_details_dao = rig.s3_upload_details_dao
    controller = rig.controller

    # Create a FileUploadBox and a FileUpload
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Set the mock to raise a MultiPartUploadConfirmError
    # This simulates S3 failing to complete the multipart upload
    # Try to complete the file upload - should raise UploadCompletionError
    storage = rig.object_storages.for_alias("test")[1]

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadConfirmError("", "", "")

    storage.complete_multipart_upload = do_error  # type: ignore[method-assign]
    with (
        raise_object_storage_error(InMemObjectStorage.MultiPartUploadConfirmError),
        pytest.raises(UploadControllerPort.UploadCompletionError) as exc_info,
    ):
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="sha256:unencrypted_checksum_here",
            encrypted_checksum=f"etag_for_{file_id}",
        )

    # Verify the exception contains the S3 upload ID
    s3_upload_id = s3_upload_details_dao.latest.s3_upload_id
    assert s3_upload_id in str(exc_info.value)
    assert not rig.file_upload_dao.latest.completed
    assert not s3_upload_details_dao.latest.completed
    assert file_upload_box_dao.latest.size == 0
    assert file_upload_box_dao.latest.file_count == 0


async def test_get_part_upload_url_with_missing_file_id(rig: JointRig):
    """Test for error handling when getting a part URL but there's no S3UploadDetails
    document with a matching file_id.
    """
    # Create a FileUploadBox and a FileUpload
    controller = rig.controller
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Manually delete the S3UploadDetails but leave the FileUpload
    await rig.s3_upload_details_dao.delete(file_id)

    # Try to get a part upload URL - should raise S3UploadDetailsNotFoundError
    with pytest.raises(UploadControllerPort.S3UploadDetailsNotFoundError) as exc_info:
        await controller.get_part_upload_url(file_id=file_id, part_no=1)

    # Verify the exception contains the correct file_id
    assert str(file_id) in str(exc_info.value)


async def test_get_part_upload_url_with_unknown_storage_alias(rig: JointRig):
    """Test for error handling when getting a part URL but the storage alias found in
    the relevant S3UploadDetails document is unknown (maybe configuration changed or
    data was migrated improperly).
    """
    # Create a FileUploadBox and a FileUpload with a valid storage alias
    controller = rig.controller
    s3_upload_details_dao = rig.s3_upload_details_dao
    box_id = await controller.create_file_upload_box(storage_alias="test")
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Manually modify the S3UploadDetails to have an unknown storage alias
    # This simulates a scenario where configuration changed or data was corrupted
    s3_details = s3_upload_details_dao.latest
    s3_details.storage_alias = "unknown_storage_alias"
    await s3_upload_details_dao.update(s3_details)

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
    file_id = await controller.initiate_file_upload(
        box_id=box_id, alias="test_file", size=1024
    )

    # Set the mock to raise a MultiPartUploadNotFoundError
    # This simulates S3 not being able to find the multipart upload
    # Try to get a part upload URL - should raise S3UploadNotFoundError
    storage = rig.object_storages.for_alias("test")[1]

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadNotFoundError("", "", "")

    storage.get_part_upload_url = do_error  # type: ignore[method-assign]
    with (
        raise_object_storage_error(InMemObjectStorage.MultiPartUploadNotFoundError),
        pytest.raises(UploadControllerPort.S3UploadNotFoundError) as exc_info,
    ):
        await controller.get_part_upload_url(file_id=file_id, part_no=1)

    # Verify the exception contains the S3 upload ID
    s3_upload_id = rig.s3_upload_details_dao.latest.s3_upload_id
    assert s3_upload_id in str(exc_info.value)


async def test_get_file_ids_for_non_existent_box(rig: JointRig):
    """Test get_file_ids_for_box with a non-existent box ID."""
    with pytest.raises(UploadControllerPort.BoxNotFoundError):
        await rig.controller.get_box_file_info(box_id=uuid4())


async def test_file_upload_report_no_file_upload(rig: JointRig):
    """Test the alt case where the file upload doesn't exist."""
    non_existent_file_id = uuid4()
    file_upload_report = FileUploadReport(
        file_id=non_existent_file_id,
        secret_id="test-secret-456",
        passed_inspection=True,
    )

    with pytest.raises(UploadControllerPort.FileUploadNotFound):
        await rig.controller.process_file_upload_report(
            file_upload_report=file_upload_report
        )


@pytest.mark.parametrize(
    "completed, state",
    [
        (False, "inbox"),
        (False, "archived"),
        (True, "init"),
    ],
)
async def test_file_upload_validator(completed: bool, state: FileUploadState):
    """Make sure the FileUpload model validator works."""
    with pytest.raises(ValueError):
        _ = FileUpload(
            id=uuid4(),
            completed=completed,
            state=state,
            box_id=uuid4(),
            checksum="test123",
            alias="test123",
            size=1024,
        )
