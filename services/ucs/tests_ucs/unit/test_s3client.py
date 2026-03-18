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

"""Unit tests for the S3Client"""

from uuid import uuid4

import pytest
import pytest_asyncio
from ghga_service_commons.utils.multinode_storage import ObjectStorages
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.providers.testing.s3 import InMemObjectStorage
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from tests_ucs.fixtures import ConfigFixture
from tests_ucs.fixtures.in_mem_obj_storage import InMemS3ObjectStorages
from tests_ucs.fixtures.utils import TEST_BUCKET, TEST_STORAGE_ALIAS, make_file_upload
from ucs.adapters.outbound.s3 import S3Client
from ucs.core.models import S3UploadDetails
from ucs.ports.outbound.storage import S3ClientPort

pytestmark = pytest.mark.asyncio


def make_s3_upload_details(
    *,
    file_id: UUID4 | None = None,
    s3_upload_id: str = "uninitialized",
    object_id: UUID4 | None = None,
) -> S3UploadDetails:
    """Make an instance of S3UploadDetails."""
    file_id = file_id or uuid4()
    object_id = object_id or uuid4()
    return S3UploadDetails(
        file_id=file_id,
        storage_alias=TEST_STORAGE_ALIAS,
        bucket_id=TEST_BUCKET,
        object_id=object_id,
        s3_upload_id=s3_upload_id,
        initiated=now_utc_ms_prec(),
    )


@pytest.fixture()
def patch_s3_calls(monkeypatch):
    """Mocks the object storage provider with an InMemObjectStorage object"""
    monkeypatch.setattr(
        f"{InMemS3ObjectStorages.__module__}.S3ObjectStorage", InMemObjectStorage
    )


@pytest.fixture(name="object_storages")
def configured_object_storages(config: ConfigFixture, patch_s3_calls) -> ObjectStorages:
    """Return a configured InMemObjectStorages instance."""
    return InMemS3ObjectStorages(config=config.config)


@pytest.fixture(name="s3_client")
def configured_s3_client(config: ConfigFixture, object_storages) -> S3ClientPort:
    """Return a configured S3Client instance plugged into an in-mem object storage."""
    return S3Client(config=config.config, object_storages=object_storages)


@pytest_asyncio.fixture(autouse=True)
async def create_default_bucket(object_storages: ObjectStorages):
    """Create the `test-inbox` bucket automatically for tests."""
    await object_storages.for_alias(TEST_STORAGE_ALIAS)[1].create_bucket(TEST_BUCKET)


async def test_init_upload(s3_client: S3ClientPort):
    """Test the happy case of starting a new multipart upload."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(file_upload=file_upload)
    assert isinstance(upload_id, str)
    assert upload_id


async def test_init_upload_with_existing_upload_in_progress(s3_client: S3ClientPort):
    """Make sure the appropriate error is raised if there's already an upload in progress."""
    file_upload = make_file_upload()
    await s3_client.init_multipart_upload(file_upload=file_upload)

    with pytest.raises(S3ClientPort.OrphanedMultipartUploadError):
        await s3_client.init_multipart_upload(file_upload=file_upload)


async def test_get_part_upload_url(s3_client: S3ClientPort):
    """Test the happy case of generating an upload url for a file part."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(file_upload=file_upload)
    s3_upload_details = make_s3_upload_details(
        file_id=file_upload.id, s3_upload_id=upload_id, object_id=file_upload.object_id
    )
    url = await s3_client.get_part_upload_url(
        s3_upload_details=s3_upload_details, part_no=1
    )
    assert str(file_upload.object_id) in url
    assert "part_no_1" in url


async def test_get_part_upload_url_when_s3_upload_not_found(s3_client: S3ClientPort):
    """Test for error handling when S3 can't find the multipart upload."""
    s3_upload_details = make_s3_upload_details(s3_upload_id="not-real")

    with pytest.raises(S3ClientPort.S3UploadNotFoundError):
        await s3_client.get_part_upload_url(
            s3_upload_details=s3_upload_details, part_no=123
        )


async def test_complete_multipart_upload(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """Test the happy case of completing a multipart upload."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(file_upload=file_upload)
    s3_upload_details = make_s3_upload_details(
        file_id=file_upload.id, s3_upload_id=upload_id, object_id=file_upload.object_id
    )

    await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)

    bucket_id, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)
    assert await storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file_upload.object_id)
    )


async def test_complete_multipart_upload_idempotent(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """Completing an already-completed upload should recover silently (object exists)."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(file_upload=file_upload)
    s3_upload_details = make_s3_upload_details(
        file_id=file_upload.id, s3_upload_id=upload_id, object_id=file_upload.object_id
    )
    await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)

    # Second call: upload ID is gone but object exists — should recover silently
    await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)

    bucket_id, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)
    assert await storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file_upload.object_id)
    )


async def test_complete_multipart_upload_not_found(s3_client: S3ClientPort):
    """Completing a non-existent upload with no object present raises UploadCompletionError."""
    s3_upload_details = make_s3_upload_details(s3_upload_id="not-real")

    with pytest.raises(S3ClientPort.S3UploadCompletionError):
        await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)


async def test_get_object_etag(s3_client: S3ClientPort):
    """Test that the ETag of a completed upload matches the expected value."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(file_upload=file_upload)
    s3_upload_details = make_s3_upload_details(
        file_id=file_upload.id, s3_upload_id=upload_id, object_id=file_upload.object_id
    )
    await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)

    etag = await s3_client.get_object_etag(
        s3_upload_details=s3_upload_details, object_id=file_upload.object_id
    )
    assert etag == f"etag_for_{file_upload.object_id}"


async def test_delete_inbox_file_completed(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """Deleting a completed upload removes the object from the bucket."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(file_upload=file_upload)
    s3_upload_details = make_s3_upload_details(
        file_id=file_upload.id, s3_upload_id=upload_id, object_id=file_upload.object_id
    )
    await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)

    await s3_client.delete_inbox_file(s3_upload_details=s3_upload_details)

    bucket_id, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)
    assert not await storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file_upload.object_id)
    )


async def test_delete_inbox_file_incomplete(s3_client: S3ClientPort):
    """Deleting an incomplete upload aborts the multipart upload."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(file_upload=file_upload)
    s3_upload_details = make_s3_upload_details(
        file_id=file_upload.id, s3_upload_id=upload_id, object_id=file_upload.object_id
    )

    await s3_client.delete_inbox_file(s3_upload_details=s3_upload_details)

    # The multipart upload is gone — completing it should now fail
    with pytest.raises(S3ClientPort.S3UploadCompletionError):
        await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)


async def test_delete_inbox_file_nothing_exists(s3_client: S3ClientPort):
    """Deleting when neither the object nor the multipart upload exist succeeds silently."""
    s3_upload_details = make_s3_upload_details(s3_upload_id="not-real")
    await s3_client.delete_inbox_file(s3_upload_details=s3_upload_details)


async def test_abort_multipart_upload(s3_client: S3ClientPort):
    """Test the happy case of aborting an in-progress multipart upload."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(file_upload=file_upload)
    s3_upload_details = make_s3_upload_details(
        file_id=file_upload.id, s3_upload_id=upload_id, object_id=file_upload.object_id
    )

    await s3_client.abort_multipart_upload(s3_upload_details=s3_upload_details)

    # The multipart upload is gone — completing it should now fail
    with pytest.raises(S3ClientPort.S3UploadCompletionError):
        await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)


async def test_abort_multipart_upload_already_gone(s3_client: S3ClientPort):
    """Aborting a non-existent upload (already aborted or never started) succeeds silently."""
    s3_upload_details = make_s3_upload_details(s3_upload_id="not-real")
    await s3_client.abort_multipart_upload(s3_upload_details=s3_upload_details)


async def test_abort_and_delete_raise_s3_upload_abort_error(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """S3UploadAbortError is raised by both abort and delete methods when
    the underlying abort fails.
    """
    s3_upload_details = make_s3_upload_details(s3_upload_id="some-upload-id")
    _, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadAbortError("", "", "")

    storage.abort_multipart_upload = do_error  # type: ignore[method-assign]

    with pytest.raises(S3ClientPort.S3UploadAbortError):
        await s3_client.delete_inbox_file(s3_upload_details=s3_upload_details)

    with pytest.raises(S3ClientPort.S3UploadAbortError):
        await s3_client.abort_multipart_upload(s3_upload_details=s3_upload_details)


async def test_unknown_storage_alias_raises_error(s3_client: S3ClientPort):
    """All S3Client methods raise UnknownStorageAliasError for unknown storage aliases."""
    file_upload = make_file_upload(storage_alias="unknown_storage_alias")
    s3_upload_details = make_s3_upload_details()
    s3_upload_details.storage_alias = "unknown_storage_alias"

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.init_multipart_upload(file_upload=file_upload)

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.get_part_upload_url(
            s3_upload_details=s3_upload_details, part_no=1
        )

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.complete_multipart_upload(s3_upload_details=s3_upload_details)

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.get_object_etag(
            s3_upload_details=s3_upload_details, object_id=s3_upload_details.object_id
        )

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.delete_inbox_file(s3_upload_details=s3_upload_details)

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.abort_multipart_upload(s3_upload_details=s3_upload_details)
