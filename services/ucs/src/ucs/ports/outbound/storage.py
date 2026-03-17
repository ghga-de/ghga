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

"""Interfaces for object storage adapters and the exception they may throw."""

from abc import ABC, abstractmethod

from hexkit.protocols.objstorage import (  # noqa: F401
    ObjectStorageProtocol as ObjectStoragePort,
)
from pydantic import UUID4

from ucs.core.models import FileUpload, S3UploadDetails


class S3ClientPort(ABC):
    """A class that isolates S3 logic and error handling from the core"""

    class OrphanedMultipartUploadError(RuntimeError):
        """Raised when a pre-existing multipart upload is unexpectedly found"""

        def __init__(self, *, file_id: UUID4, bucket_id: str):
            msg = (
                f"An S3 multipart upload already exists for file ID {file_id} and"
                + f" bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class S3UploadNotFoundError(RuntimeError):
        """Raised when the local DB has a record of an S3 multipart upload but S3 itself doesn't."""

        def __init__(self, *, bucket_id: str, s3_upload_id: str):
            msg = (
                "S3 object storage does not contain a multipart upload with ID"
                + f" {s3_upload_id} in bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class UnknownStorageAliasError(RuntimeError):
        """Thrown when the requested storage location is not configured.
        The given parameter given should be a configured alias, but is not.
        """

        def __init__(self, *, storage_alias: str):
            message = f"No storage node exists for alias {storage_alias}."
            super().__init__(message)

    class S3UploadCompletionError(RuntimeError):
        """Raised when completing an S3 multipart upload results in an error."""

        def __init__(self, *, file_id: UUID4, s3_upload_id: str, bucket_id: str):
            msg = (
                f"Failed to complete S3 multipart upload with ID {s3_upload_id} for"
                + f" file ID {file_id} in bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class S3UploadAbortError(RuntimeError):
        """Raised when aborting an S3 multipart upload results in an error."""

        def __init__(self, *, file_id: UUID4, s3_upload_id: str, bucket_id: str):
            msg = (
                f"Failed to abort S3 multipart upload with ID {s3_upload_id} for"
                + f" file ID {file_id} in bucket ID {bucket_id}."
            )
            super().__init__(msg)

    @abstractmethod
    def get_bucket_id_for_alias(self, *, storage_alias: str) -> str:
        """Retrieve the bucket ID for a given storage alias.

        Raises `UnknownStorageAliasError` if the storage alias is not known.
        """

    @abstractmethod
    async def init_multipart_upload(self, *, file_upload: FileUpload) -> str:
        """Initiate a new multipart upload for a FileUpload.

        Returns a str containing the multipart upload ID.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `OrphanedMultipartUploadError` if an S3 upload is already in progress.
        """

    @abstractmethod
    async def get_part_upload_url(
        self, *, s3_upload_details: S3UploadDetails, part_no: int
    ) -> str:
        """Get a pre-signed URL to upload a specific part of a multipart upload.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadNotFoundError` if the multipart upload can't be found in S3.
        """

    @abstractmethod
    async def complete_multipart_upload(
        self, *, s3_upload_details: S3UploadDetails
    ) -> None:
        """Instruct S3 to assemble all uploaded parts into the final object.

        Recovers idempotently if the upload was already completed (object exists).

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadCompletionError` if the upload cannot be completed or found.
        """

    @abstractmethod
    async def get_object_etag(
        self, *, s3_upload_details: S3UploadDetails, object_id: UUID4
    ) -> str:
        """Return the ETag of an object in the inbox bucket (quotes stripped).

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
        """

    @abstractmethod
    async def delete_inbox_file(self, *, s3_upload_details: S3UploadDetails) -> None:
        """Delete a fully uploaded file from the inbox, or abort any stale multipart.

        If the object exists it is deleted. If only an in-progress multipart upload
        exists, that is aborted instead. A missing multipart upload is tolerated.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadAbortError` if an abort is required but fails.
        """

    @abstractmethod
    async def abort_multipart_upload(
        self, *, s3_upload_details: S3UploadDetails
    ) -> None:
        """Abort an in-progress multipart upload. Tolerates a missing upload.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadAbortError` if the abort fails.
        """
