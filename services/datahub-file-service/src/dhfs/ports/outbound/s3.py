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

"""Port definition for a class that communicates with S3"""

from abc import ABC, abstractmethod

from dhfs.core.models import FileUpload


class S3ClientPort(ABC):
    """Performs S3 upload/download operations with error handling"""

    class S3Error(RuntimeError):
        """Base error class for all S3 errors"""

    class CriticalS3Error(S3Error):
        """Raised for S3 problems that must be resolved before DHFS can continue."""

    class BucketNotFoundError(CriticalS3Error):
        """Raised when a given bucket does not exist in S3."""

        def __init__(self, *, bucket_id: str) -> None:
            self.bucket_id = bucket_id
            msg = f"Could not find any bucket with the ID '{bucket_id}'."
            super().__init__(msg)

    class S3OperationError(S3Error):
        """Raised when there's a non-critical problem with an operation in S3"""

    class ObjectNotFoundError(S3OperationError):
        """Raised when a given object does not exist in S3"""

        def __init__(self, *, object_id: str):
            msg = f"Cannot get download URL for object {object_id} because it doesn't exist."
            super().__init__(msg)

    class DownloadError(S3OperationError):
        """Raised when there's a problem downloading a file from the inbox."""

        def __init__(self, *, bucket_id: str, object_id: str, status_code: int):
            msg = (
                f"Received a {status_code} error when trying to download object {object_id}"
                + f" from bucket {bucket_id}."
            )
            super().__init__(msg)

    class UploadInitError(S3OperationError):
        """Raised when there's a problem initiating an upload."""

        def __init__(self, *, object_id: str):
            msg = (
                f"Cannot create a multipart upload for object {object_id} because an"
                + " ongoing upload for the same object already exists."
            )
            super().__init__(msg)

    class UploadURLMissingUploadError(S3OperationError):
        """Raised when trying to generate a presigned upload URL for an upload that doesn't exist"""

        def __init__(self, *, upload_id: str):
            msg = (
                f"Failed to get part upload URL for upload {upload_id} because the"
                + " upload does not exist."
            )
            super().__init__(msg)

    class UploadPartError(S3OperationError):
        """Raised when there's a problem uploading a file part."""

        def __init__(
            self, *, object_id: str, part_no: int, status_code: int, detail: str
        ):
            msg = (
                f"Failed to upload part {part_no} for object {object_id}. Status"
                + f" code is {status_code}. Detail: {detail}"
            )
            super().__init__(msg)

    class UploadCompletionError(S3OperationError):
        """Raised when there's a problem completing an upload.

        This serves as a catch-all for unexpected errors during upload completion.
        """

        def __init__(self, *, upload_id: str, object_id: str):
            msg = (
                f"Couldn't complete upload {upload_id} for object {object_id}"
                + " because the upload doesn't exist."
            )
            super().__init__(msg)

    class IntegrityError(S3OperationError):
        """Raised during upload completion when the number or size of uploaded parts
        doesn't match what is expected.
        """

        def __init__(self, *, upload_id: str, object_id: str):
            msg = (
                f"S3 rejected upload {upload_id} for object {object_id} due to a"
                + " difference in the expected part count or size."
            )
            super().__init__(msg)

    class BadPartMD5Error(S3OperationError):
        """Raised when the MD5 for a file part doesn't match the expected value"""

        def __init__(self, *, part_no: int, object_id: str):
            msg = (
                f"Failed to upload part {part_no} for file {object_id} because the"
                + " MD5 hash didn't match the expected value."
            )
            super().__init__(msg)

    class S3CleanupError(S3Error):
        """Raised when there's a problem deleting an object from S3"""

        def __init__(self, *, bucket_id: str, object_id: str):
            msg = f"Failed to delete object {object_id} from the {bucket_id} bucket."
            super().__init__(msg)

    @abstractmethod
    async def get_is_file_in_inbox(self, *, file: FileUpload) -> bool:
        """Return a bool indicating whether the file exists in the inbox.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        """

    @abstractmethod
    async def list_files_in_interrogation_bucket(self) -> list[str]:
        """Returns a list of object IDs from the interrogation bucket.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        """

    @abstractmethod
    async def fetch_file_content_range(
        self,
        *,
        bucket_id: str,
        object_id: str,
        start: int,
        stop: int,
        bust_cache: bool = False,
    ) -> bytes:
        """Download a single file part for the bytes in range `start` - `stop` (exclusive end, like Python slicing).

        `bust_cache` will refresh the download url used for the object.

        Raises:
        - BucketNotFoundError if the inbox bucket doesn't exist.
        - ObjectNotFoundError if the file doesn't exist in the inbox.
        - DownloadError if the download request fails or returns an unexpected status code.
        """
        ...

    @abstractmethod
    async def init_interrogation_bucket_upload(self, *, object_id: str) -> str:
        """Start a multipart upload to the interrogation bucket.

        If the object already exists in the interrogation bucket for any reason, it will
        be deleted and the interrogation process proceeds as if the object had never
        been there.

        Raises:
        - UploadInitError if an ongoing upload already exists for the object or if an unexpected error occurs.
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        """
        ...

    @abstractmethod
    async def upload_file_part(
        self,
        *,
        upload_id: str,
        object_id: str,
        part_no: int,
        part_md5: bytes,
        part: bytes,
    ) -> None:
        """Upload a single re-encrypted file part.

        Raises:
        - BadPartMD5Error if the specified MD5 doesn't match the MD5 calculated by S3.
        - BucketNotFoundError if the interrogation bucket is missing.
        - UploadPartError if any other error causes the part upload to fail.
        """
        ...

    @abstractmethod
    async def complete_upload(
        self, *, upload_id: str, object_id: str, part_count: int
    ) -> str:
        """Complete a multipart upload for an object in the interrogation bucket.

        Returns the object's ETag (which is the MD5 checksum of the encrypted file).

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        - PartCountMismatchError if the number of uploaded parts doesn't match the expected count.
        - UploadCompletionError if the upload doesn't exist or another error prevents completion.
        """
        ...

    @abstractmethod
    async def abort_upload(self, *, upload_id: str, object_id: str) -> None:
        """Abort a multipart upload for an object in the interrogation bucket.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        - S3Error if an unexpected error occurs while aborting the upload.
        """
        ...

    @abstractmethod
    async def remove_file(self, *, object_id: str) -> None:
        """Remove a file from the interrogation bucket.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        - S3CleanupError if an unexpected error occurs while deleting the file.
        """
        ...
