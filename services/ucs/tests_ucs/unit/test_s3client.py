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

"""Unit tests for the S3Client"""

import pytest
import pytest_asyncio
from ghga_service_commons.utils.multinode_storage import ObjectStorages
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.providers.testing.objstorage import InMemObjectStorage

from tests_ucs.fixtures import ConfigFixture
from tests_ucs.fixtures.in_mem_obj_storage import InMemS3ObjectStorages
from tests_ucs.fixtures.utils import TEST_BUCKET, TEST_STORAGE_ALIAS, make_file_upload
from ucs.adapters.outbound.s3 import S3Client
from ucs.core.models import FileUpload, FileUploadBasics
from ucs.ports.outbound.storage import S3ClientPort

pytestmark = pytest.mark.asyncio


def _to_basics(file_upload: FileUpload) -> FileUploadBasics:
    """Extract a FileUploadBasics from a FileUpload."""
    return FileUploadBasics(
        **{
            field: getattr(file_upload, field)
            for field in FileUploadBasics.model_fields
        }
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
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    assert isinstance(upload_id, str)
    assert upload_id


async def test_existing_uploads_translated_as_orphaned_error(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """Test that init_multipart_upload() translates MultipleActiveUploadsError and
    MultiPartUploadAlreadyExistsError into OrphanedMultipartUploadError.
    """
    file_upload = make_file_upload()
    _, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultipleActiveUploadsError("", "", [])

    async def do_error2(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadAlreadyExistsError("", "")

    for error_fn in [do_error, do_error2]:
        storage.init_multipart_upload = error_fn  # type: ignore[method-assign]

        with pytest.raises(S3ClientPort.OrphanedMultipartUploadError):
            await s3_client.init_multipart_upload(
                file_upload_basics=_to_basics(file_upload)
            )


async def test_get_part_upload_url(s3_client: S3ClientPort):
    """Test the happy case of generating an upload url for a file part."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    file_upload = file_upload.model_copy(update={"s3_upload_id": upload_id})
    url = await s3_client.get_part_upload_url(file_upload=file_upload, part_no=1)
    assert str(file_upload.object_id) in url
    assert "part_no_1" in url


async def test_get_part_upload_url_when_s3_upload_not_found(s3_client: S3ClientPort):
    """Test for error handling when S3 can't find the multipart upload."""
    file_upload = make_file_upload(s3_upload_id="not-real")

    with pytest.raises(S3ClientPort.S3UploadNotFoundError):
        await s3_client.get_part_upload_url(file_upload=file_upload, part_no=123)


async def test_complete_multipart_upload(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """Test the happy case of completing a multipart upload."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    file_upload = file_upload.model_copy(update={"s3_upload_id": upload_id})

    await s3_client.complete_multipart_upload(file_upload=file_upload)

    bucket_id, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)
    assert await storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file_upload.object_id)
    )


async def test_complete_multipart_upload_idempotent(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """Completing an already-completed upload should recover silently (object exists)."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    file_upload = file_upload.model_copy(update={"s3_upload_id": upload_id})
    await s3_client.complete_multipart_upload(file_upload=file_upload)

    # Second call: upload ID is gone but object exists — should recover silently
    await s3_client.complete_multipart_upload(file_upload=file_upload)

    bucket_id, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)
    assert await storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file_upload.object_id)
    )


async def test_complete_multipart_upload_not_found(s3_client: S3ClientPort):
    """Completing a non-existent upload with no object present raises UploadCompletionError."""
    file_upload = make_file_upload(s3_upload_id="not-real")

    with pytest.raises(S3ClientPort.S3UploadCompletionError):
        await s3_client.complete_multipart_upload(file_upload=file_upload)


async def test_get_object_etag(s3_client: S3ClientPort):
    """Test that the ETag of a completed upload matches the expected value."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    file_upload = file_upload.model_copy(update={"s3_upload_id": upload_id})
    await s3_client.complete_multipart_upload(file_upload=file_upload)

    etag = await s3_client.get_object_etag(
        file_upload=file_upload, object_id=file_upload.object_id
    )
    assert etag == f"etag_for_{file_upload.object_id}"


async def test_get_object_size(s3_client: S3ClientPort):
    """Test that the size of a completed upload is returned."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    file_upload = file_upload.model_copy(update={"s3_upload_id": upload_id})
    await s3_client.complete_multipart_upload(file_upload=file_upload)

    size = await s3_client.get_object_size(
        file_upload=file_upload, object_id=file_upload.object_id
    )
    assert size == 1024  # the dummy value returned by the InMem S3 fixture


async def test_delete_inbox_file_completed(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """Deleting a completed upload removes the object from the bucket."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    file_upload = file_upload.model_copy(update={"s3_upload_id": upload_id})
    await s3_client.complete_multipart_upload(file_upload=file_upload)

    await s3_client.delete_inbox_file(file_upload=file_upload)

    bucket_id, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)
    assert not await storage.does_object_exist(
        bucket_id=bucket_id, object_id=str(file_upload.object_id)
    )


async def test_delete_inbox_file_incomplete(s3_client: S3ClientPort):
    """Test that deleting an incomplete upload aborts the multipart upload."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    file_upload = file_upload.model_copy(update={"s3_upload_id": upload_id})

    await s3_client.delete_inbox_file(file_upload=file_upload)

    # The multipart upload is gone — completing it should now fail
    with pytest.raises(S3ClientPort.S3UploadCompletionError):
        await s3_client.complete_multipart_upload(file_upload=file_upload)


async def test_delete_inbox_file_nothing_exists(s3_client: S3ClientPort):
    """Deleting when neither the object nor the multipart upload exist succeeds silently."""
    file_upload = make_file_upload(s3_upload_id="not-real")
    await s3_client.delete_inbox_file(file_upload=file_upload)


async def test_abort_multipart_upload(s3_client: S3ClientPort):
    """Test the happy case of aborting an in-progress multipart upload."""
    file_upload = make_file_upload()
    upload_id = await s3_client.init_multipart_upload(
        file_upload_basics=_to_basics(file_upload)
    )
    file_upload = file_upload.model_copy(update={"s3_upload_id": upload_id})

    await s3_client.abort_multipart_upload(
        storage_alias=file_upload.storage_alias,
        object_id=str(file_upload.object_id),
        s3_upload_id=file_upload.s3_upload_id,
    )

    # The multipart upload is gone — completing it should now fail
    with pytest.raises(S3ClientPort.S3UploadCompletionError):
        await s3_client.complete_multipart_upload(file_upload=file_upload)


async def test_abort_multipart_upload_already_gone(s3_client: S3ClientPort):
    """Aborting a non-existent upload (already aborted or never started) succeeds silently."""
    file_upload = make_file_upload(s3_upload_id="not-real")
    await s3_client.abort_multipart_upload(
        storage_alias=file_upload.storage_alias,
        object_id=str(file_upload.object_id),
        s3_upload_id=file_upload.s3_upload_id,
    )


async def test_abort_and_delete_raise_s3_upload_abort_error(
    s3_client: S3ClientPort, object_storages: ObjectStorages
):
    """S3UploadAbortError is raised by both abort and delete methods when
    the underlying abort fails.
    """
    file_upload = make_file_upload(s3_upload_id="some-upload-id")
    _, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.MultiPartUploadAbortError("", "", "")

    storage.abort_multipart_upload = do_error  # type: ignore[method-assign]

    with pytest.raises(S3ClientPort.S3UploadAbortError):
        await s3_client.delete_inbox_file(file_upload=file_upload)

    with pytest.raises(S3ClientPort.S3UploadAbortError):
        await s3_client.abort_multipart_upload(
            storage_alias=file_upload.storage_alias,
            object_id=str(file_upload.object_id),
            s3_upload_id=file_upload.s3_upload_id,
        )


async def test_unknown_storage_alias_raises_error(s3_client: S3ClientPort):
    """All S3Client methods raise UnknownStorageAliasError for unknown storage aliases."""
    file_upload = make_file_upload(storage_alias="unknown_storage_alias")

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.init_multipart_upload(
            file_upload_basics=_to_basics(file_upload)
        )

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.get_part_upload_url(file_upload=file_upload, part_no=1)

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.complete_multipart_upload(file_upload=file_upload)

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.get_object_etag(
            file_upload=file_upload, object_id=file_upload.object_id
        )

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.get_object_size(
            file_upload=file_upload, object_id=file_upload.object_id
        )

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.delete_inbox_file(file_upload=file_upload)

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.abort_multipart_upload(
            storage_alias=file_upload.storage_alias,
            object_id=str(file_upload.object_id),
            s3_upload_id=file_upload.s3_upload_id,
        )

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.abort_multipart_upload(
            storage_alias=file_upload.storage_alias,
            object_id=str(file_upload.object_id),
            s3_upload_id=file_upload.s3_upload_id,
            file_id=file_upload.id,
        )

    with pytest.raises(S3ClientPort.UnknownStorageAliasError):
        await s3_client.list_all_multipart_uploads(
            storage_alias=file_upload.storage_alias
        )


@pytest.mark.parametrize(
    "method_name, storage_method_name",
    [
        ("init_multipart_upload", "init_multipart_upload"),
        ("get_part_upload_url", "get_part_upload_url"),
        ("complete_multipart_upload", "complete_multipart_upload"),
        ("get_object_etag", "get_object_etag"),
        ("get_object_size", "get_object_size"),
        ("delete_inbox_file", "does_object_exist"),
        ("abort_multipart_upload", "abort_multipart_upload"),
        ("list_all_multipart_uploads", "get_all_multipart_uploads"),
    ],
)
async def test_bucket_not_found_raises_bucket_not_found_error(
    s3_client: S3ClientPort,
    object_storages: ObjectStorages,
    method_name: str,
    storage_method_name: str,
):
    """Test that the S3Client translates hexkit's BucketNotFoundError into
    S3ClientPort.BucketNotFoundError.
    """
    file_upload = make_file_upload(s3_upload_id="some-upload-id")
    _, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.BucketNotFoundError(file_upload.bucket_id)

    setattr(storage, storage_method_name, do_error)

    kwargs: dict = {"file_upload": file_upload}
    if method_name == "init_multipart_upload":
        kwargs = {"file_upload_basics": _to_basics(file_upload)}
    elif method_name == "get_part_upload_url":
        kwargs["part_no"] = 1
    elif method_name in ("get_object_etag", "get_object_size"):
        kwargs["object_id"] = file_upload.object_id
    elif method_name == "abort_multipart_upload":
        kwargs = {
            "storage_alias": file_upload.storage_alias,
            "object_id": str(file_upload.object_id),
            "s3_upload_id": file_upload.s3_upload_id,
        }
    elif method_name == "list_all_multipart_uploads":
        kwargs = {"storage_alias": file_upload.storage_alias}

    with pytest.raises(S3ClientPort.BucketNotFoundError):
        await getattr(s3_client, method_name)(**kwargs)


async def test_object_not_found_raises_s3_object_not_found_error(
    s3_client: S3ClientPort,
    object_storages: ObjectStorages,
):
    """Test that S3Client.get_object_etag() and .get_object_size() translate
    ObjectNotFoundError into S3ClientPort.S3ObjectNotFoundError.
    """
    file_upload = make_file_upload()
    _, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)

    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.ObjectNotFoundError(
            bucket_id=file_upload.bucket_id, object_id=str(file_upload.object_id)
        )

    for method_name in ["get_object_etag", "get_object_size"]:
        setattr(storage, method_name, do_error)

        with pytest.raises(S3ClientPort.S3ObjectNotFoundError):
            await getattr(s3_client, method_name)(
                file_upload=file_upload, object_id=file_upload.object_id
            )


@pytest.mark.parametrize(
    "method_name, storage_method_name, extra_kwargs",
    [
        ("init_multipart_upload", "init_multipart_upload", {}),
        ("get_part_upload_url", "get_part_upload_url", {"part_no": 1}),
        ("complete_multipart_upload", "complete_multipart_upload", {}),
        ("get_object_etag", "get_object_etag", {"_object_id": True}),
        ("get_object_size", "get_object_size", {"_object_id": True}),
        ("delete_inbox_file", "does_object_exist", {}),
        ("abort_multipart_upload", "abort_multipart_upload", {}),
        ("list_all_multipart_uploads", "get_all_multipart_uploads", {}),
    ],
)
async def test_generic_storage_error_raises_s3_operation_error(
    s3_client: S3ClientPort,
    object_storages: ObjectStorages,
    method_name: str,
    storage_method_name: str,
    extra_kwargs: dict,
):
    """Make sure generic S3 error classes are are translated into
    S3ClientPort.S3OperationError.
    """
    file_upload = make_file_upload(s3_upload_id="some-upload-id")
    _, storage = object_storages.for_alias(TEST_STORAGE_ALIAS)

    # Patch the given storage method with a function that raises a generic error
    async def do_error(*args, **kwargs):
        raise ObjectStorageProtocol.ObjectStorageProtocolError("test")

    setattr(storage, storage_method_name, do_error)

    # Declare any kwargs for the different method calls
    kwargs: dict = {"file_upload": file_upload}
    if method_name == "init_multipart_upload":
        kwargs = {"file_upload_basics": _to_basics(file_upload)}
    elif method_name == "abort_multipart_upload":
        kwargs = {
            "storage_alias": file_upload.storage_alias,
            "object_id": str(file_upload.object_id),
            "s3_upload_id": file_upload.s3_upload_id,
        }
    elif method_name == "list_all_multipart_uploads":
        kwargs = {"storage_alias": file_upload.storage_alias}
    if extra_kwargs.pop("_object_id", False):
        kwargs["object_id"] = file_upload.object_id
    kwargs.update(extra_kwargs)

    # Call the method and verify that it was translated as the generic S3OperationError
    with pytest.raises(S3ClientPort.S3OperationError):
        await getattr(s3_client, method_name)(**kwargs)
