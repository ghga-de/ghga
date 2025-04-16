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
"""Describes API of classes that interface between inbound requests and object storage."""

from abc import ABC, abstractmethod

from hexkit.providers.s3 import S3ObjectStorage


class S3ObjectStoragesPort(ABC):
    """S3-specific multi-node object storage instance.

    Provides access to object storage instances by alias on demand.
    This class is used instead of the one provided by ghga-service-commons because
    the bucket/config tuple returned by that version does not suit the needs of the SMS.
    """

    class AliasNotConfiguredError(RuntimeError):
        """Raised when a requested object storage alias is not configured."""

        def __init__(self, *, alias: str):
            super().__init__(f"The object storage alias '{alias}' is not configured.")

    @abstractmethod
    def for_alias(self, endpoint_alias: str) -> S3ObjectStorage:
        """Return the object storage associated with the given alias.

        If the storage has not been accessed yet, it will be created and stored.

        Raises:
        - `AliasNotConfiguredError` if the alias does not exist in configuration.
        """
        ...


class ObjectsHandlerPort(ABC):
    """Class for multi-node (federated) object storage management."""

    class OperationError(RuntimeError):
        """Catch-all exception for errors that aren't defined below."""

        def __init__(self):
            msg = "An error occurred while performing the object-storage operation."
            super().__init__(msg)

    class NotFoundError(RuntimeError):
        """Raised when an object or bucket does not exist."""

    class BucketNotFoundError(NotFoundError):
        """Raised when a bucket does not exist."""

        def __init__(self, *, bucket_id: str):
            super().__init__(f"Bucket with ID '{bucket_id}' does not exist.")

    class ObjectNotFoundError(NotFoundError):
        """Raised when an object does not exist."""

        def __init__(self, *, bucket_id: str, object_id: str):
            msg = f"Object '{object_id}' in bucket '{bucket_id}' does not exist."
            super().__init__(msg)

    class InvalidIdError(RuntimeError):
        """Base class for errors raised when a bucket or object ID is invalid."""

    class InvalidBucketIdError(InvalidIdError):
        """Raised when a bucket ID is invalid."""

        def __init__(self, *, bucket_id: str):
            super().__init__(f"Bucket ID '{bucket_id}' is invalid.")

    class InvalidObjectIdError(InvalidIdError):
        """Raised when an object ID is invalid."""

        def __init__(self, *, object_id: str):
            super().__init__(f"Object ID '{object_id}' is invalid.")

    @abstractmethod
    async def does_object_exist(
        self, alias: str, bucket_id: str, object_id: str
    ) -> bool:
        """Check if an object exists in the specified bucket for the given alias.

        Returns `False` if the object is not in the bucket, otherwise `True`.

        Raises:
        - `AliasNotConfiguredError`: When the alias does not exist in configuration.
        - `BucketNotFoundError`: When the bucket does not exist.
        - `InvalidBucketIdError`: When the bucket ID is invalid.
        - `InvalidObjectIdError`: When the object ID is invalid.
        """
        ...

    @abstractmethod
    async def empty_bucket(self, alias: str, bucket_id: str) -> None:
        """Delete all objects in the specified bucket for the given alias.

        Raises:
        - `AliasNotConfiguredError`: When the alias does not exist in configuration.
        - `InvalidBucketIdError`: When the bucket ID is invalid.
        - `ObjectNotFoundError`: When an object is unexpectedly absent.
        """
        ...

    @abstractmethod
    async def list_objects(self, alias: str, bucket_id: str) -> list[str]:
        """List all objects in the specified bucket for the given alias.

        Returns a list of object IDs contained by the bucket.

        Raises:
        - `AliasNotConfiguredError`: When the alias does not exist in configuration.
        - `BucketNotFoundError`: When the bucket does not exist.
        - `InvalidBucketIdError`: When the bucket ID is invalid.
        """
        ...
