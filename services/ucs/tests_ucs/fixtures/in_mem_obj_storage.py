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

"""Mock object storage class"""

from collections import defaultdict
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from ghga_service_commons.utils.multinode_storage import (
    ObjectStorages,
    S3ObjectStoragesConfig,
)
from hexkit.providers.s3 import S3Config, S3ObjectStorage

UploadID = str
BucketID = str
ObjectID = str
File = Any


@contextmanager
def raise_object_storage_error(error_cls: type[Exception]):
    """Set InMemObjectStorage class var `error` so the next call will raise that error."""
    InMemObjectStorage.error = error_cls
    yield
    InMemObjectStorage.error = None


class InMemObjectStorage:
    """In-memory object storage mock just the method used in this service"""

    class ObjectNotFoundError(S3ObjectStorage.ObjectNotFoundError):
        """Dummy error"""

        def __init__(self):
            pass

    class MultiPartUploadAlreadyExistsError(
        S3ObjectStorage.MultiPartUploadAlreadyExistsError
    ):
        """Dummy error"""

        def __init__(self):
            pass

    class MultiPartUploadNotFoundError(S3ObjectStorage.MultiPartUploadNotFoundError):
        """Dummy error"""

        def __init__(self):
            pass

    class MultiPartUploadConfirmError(S3ObjectStorage.MultiPartUploadConfirmError):
        """Dummy error"""

        def __init__(self):
            pass

    class MultiPartUploadAbortError(S3ObjectStorage.MultiPartUploadAbortError):
        """Dummy error"""

        def __init__(self):
            pass

    error: type[Exception] | None = None

    def __init__(self, *, config: S3Config):
        """Set bucket ID"""
        self.objects: dict[BucketID, set[ObjectID]] = defaultdict(set)
        self.uploads: dict[BucketID, dict[ObjectID, UploadID]] = defaultdict(dict)

    def _do_conditional_raise(self):
        """Raise specified error if set"""
        if self.error:
            raise self.error()

    async def does_object_exist(
        self, *, bucket_id: str, object_id: str, object_md5sum: str | None = None
    ) -> bool:
        """Return a bool indicating if the object ID exists in the bucket specified."""
        self._do_conditional_raise()
        return object_id in self.objects[bucket_id]

    async def does_upload_exist(
        self, *, upload_id: str, bucket_id: str, object_id: str
    ) -> bool:
        """Return a bool indicating whether a given upload ID exists"""
        self._do_conditional_raise()
        if upload_id := self.uploads[bucket_id].get(object_id, ""):
            return upload_id == upload_id
        return False

    async def delete_object(self, *, bucket_id: str, object_id: str) -> None:
        """Delete an object with the specified id (`object_id`) in the bucket with the
        specified id (`bucket_id`).
        """
        self._do_conditional_raise()
        if not await self.does_object_exist(bucket_id=bucket_id, object_id=object_id):
            raise self.ObjectNotFoundError()
        self.objects[bucket_id].remove(object_id)

    async def get_part_upload_url(
        self,
        *,
        upload_id: str,
        bucket_id: str,
        object_id: str,
        part_number: int,
    ):
        """Return a made-up part upload url incorporating the storage details and part number"""
        self._do_conditional_raise()
        return (
            f"https://s3.example.com/{bucket_id}/{object_id}"
            + f"?part={part_number}&uploadId={upload_id}"
        )

    async def init_multipart_upload(self, *, bucket_id: str, object_id: str):
        """Add a new upload for the chosen bucket and object ID"""
        self._do_conditional_raise()
        if object_id in self.uploads[bucket_id]:
            raise self.MultiPartUploadAlreadyExistsError()
        upload_id = str(uuid4())
        self.uploads[bucket_id][object_id] = upload_id
        return upload_id

    async def complete_multipart_upload(
        self, *, upload_id: str, bucket_id: str, object_id: str
    ):
        """Complete the specified upload and add the object ID to the objects dict"""
        self._do_conditional_raise()
        if not await self.does_upload_exist(
            upload_id=upload_id, bucket_id=bucket_id, object_id=object_id
        ):
            raise self.MultiPartUploadNotFoundError()
        self.uploads[bucket_id].pop(object_id)
        self.objects[bucket_id].add(object_id)

    async def abort_multipart_upload(
        self, *, upload_id: str, bucket_id: str, object_id: str
    ):
        """Remove the specified upload and do not add the object ID to the objects dict"""
        self._do_conditional_raise()
        if not await self.does_upload_exist(
            upload_id=upload_id, bucket_id=bucket_id, object_id=object_id
        ):
            raise self.MultiPartUploadNotFoundError()


class InMemS3ObjectStorages(ObjectStorages):
    """S3 specific multi node object storage instance.

    Object storage instances for a given alias should be instantiated lazily on demand.
    """

    def __init__(self, *, config: S3ObjectStoragesConfig):
        self._config = config
        self._data: dict[str, S3ObjectStorage] = {}

    def for_alias(self, endpoint_alias: str) -> tuple[str, S3ObjectStorage]:
        """Get bucket ID and object storage instance for a specific alias."""
        node_config = self._config.object_storages[endpoint_alias]
        try:
            return node_config.bucket, self._data[node_config.bucket]
        except KeyError:
            self._data[node_config.bucket] = S3ObjectStorage(
                config=node_config.credentials
            )
            return node_config.bucket, self._data[node_config.bucket]
