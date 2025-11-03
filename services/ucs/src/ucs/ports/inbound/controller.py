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

"""Defines the main upload controller class"""

from abc import ABC, abstractmethod

from ghga_event_schemas.pydantic_ import FileUploadReport
from pydantic import UUID4


class UploadControllerPort(ABC):
    """A class for managing file uploads"""

    class UploadError(RuntimeError):
        """Base error class for all upload errors"""

    class IncompleteUploadsError(UploadError):
        """Raised when trying to lock a FileUploadBox for which at least one incomplete
        FileUpload exists.
        """

        def __init__(self, *, box_id: UUID4, file_ids: list[UUID4]):
            msg = f"Cannot lock box {box_id} because these files are incomplete: {file_ids}"
            super().__init__(msg)

    class S3UploadDetailsNotFoundError(UploadError):
        """Raised when the expected S3 upload details aren't found in the local DB.

        This happens when there is a FileUpload object but no matching S3UploadDetails.
        """

        def __init__(self, *, file_id: UUID4):
            msg = f"Failed to find S3 multipart upload details for file ID {file_id}."
            super().__init__(msg)

    class S3UploadNotFoundError(UploadError):
        """Raised when the local DB has a record of an S3 multipart upload but S3 itself doesn't."""

        def __init__(self, *, bucket_id: str, s3_upload_id: str):
            msg = (
                "S3 object storage does not contain a multipart upload with ID"
                + f" {s3_upload_id} in bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class UploadAbortError(UploadError):
        """Raised when aborting an S3 multipart upload results in an error."""

        def __init__(self, *, file_id: UUID4, s3_upload_id: str, bucket_id: str):
            msg = (
                f"Failed to abort S3 multipart upload with ID {s3_upload_id} for"
                + f" file ID {file_id} in bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class UploadCompletionError(UploadError):
        """Raised when completing an S3 multipart upload results in an error"""

        def __init__(self, *, file_id: UUID4, s3_upload_id: str, bucket_id: str):
            msg = (
                f"Failed to complete S3 multipart upload with ID {s3_upload_id} for"
                + f" file ID {file_id} in bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class OrphanedMultipartUploadError(UploadError):
        """Raised when a pre-existing multipart upload is unexpectedly found"""

        def __init__(self, *, file_id: UUID4, bucket_id: str):
            msg = (
                f"An S3 multipart upload already exists for file ID {file_id} and"
                + f" bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class UnknownStorageAliasError(UploadError):
        """Thrown when the requested storage location is not configured.
        The given parameter given should be a configured alias, but is not.
        """

        def __init__(self, *, storage_alias: str):
            message = f"No storage node exists for alias {storage_alias}."
            super().__init__(message)

    class LockedBoxError(UploadError):
        """Raised when a user tries to perform an action that requires the Box to be
        unlocked, but the Box is locked.
        """

        def __init__(self, *, box_id: UUID4):
            msg = f"Can't perform this action because FileUploadBox with ID {box_id} is locked"
            super().__init__(msg)

    class FileUploadAlreadyExists(UploadError):
        """Raised when a FileUpload can't be created for a given box ID and file alias
        because one already exists.
        """

        def __init__(self, *, alias: str):
            msg = (
                f"Failed to create a FileUpload for file alias {alias} because"
                + " one already exists."
            )
            super().__init__(msg)

    class BoxNotFoundError(UploadError):
        """Raised when a FileUploadBox isn't found in the DB"""

        def __init__(self, *, box_id: UUID4):
            msg = f"FileUploadBox with ID {box_id} not found."
            super().__init__(msg)

    class FileUploadNotFound(UploadError):
        """Raised when a FileUpload isn't found in the DB"""

        def __init__(self, *, file_id: UUID4):
            msg = f"FileUpload with ID {file_id} not found."
            super().__init__(msg)

    @abstractmethod
    async def initiate_file_upload(
        self, *, box_id: UUID4, alias: str, size: int
    ) -> UUID4:
        """Initialize a new multipart upload and return the file ID.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `LockedBoxError` if the box exists but is locked.
        - `FileUploadAlreadyExists` if there's already a FileUpload for this alias.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `OrphanedMultipartUploadError` if an S3 upload is already in progress.
        """
        ...

    @abstractmethod
    async def get_part_upload_url(self, *, file_id: UUID4, part_no: int) -> str:
        """
        Create and return a pre-signed URL to upload the bytes for the file part with
        the given number of the upload with the given file ID.

        Raises:
        - `S3UploadDetailsNotFoundError` if no upload details are found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `S3UploadNotFoundError` if the S3 multipart upload can't be found.
        """
        ...

    @abstractmethod
    async def complete_file_upload(
        self, *, box_id: UUID4, file_id: UUID4, checksum: str
    ) -> None:
        """Instruct S3 to complete a multipart upload.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
        - `BoxNotFoundError` if the FileUploadBox isn't found.
        - `LockedBoxError` if the box exists but is locked.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadCompletionError` if there's an error while telling S3 to complete the upload.
        """
        ...

    @abstractmethod
    async def remove_file_upload(self, *, box_id: UUID4, file_id: UUID4) -> None:
        """Remove a file upload and cancel the ongoing upload if applicable.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `LockedBoxError` if the box exists but is locked.
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        ...

    @abstractmethod
    async def create_file_upload_box(self, *, storage_alias: str) -> UUID4:
        """Create a new FileUploadBox with the given S3 storage alias.
        Returns the UUID4 id of the created FileUploadBox.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        """
        ...

    @abstractmethod
    async def lock_file_upload_box(self, *, box_id: UUID4) -> None:
        """Lock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        """
        ...

    @abstractmethod
    async def unlock_file_upload_box(self, *, box_id: UUID4) -> None:
        """Unlock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        """
        ...

    @abstractmethod
    async def get_file_ids_for_box(self, *, box_id: UUID4) -> list[UUID4]:
        """Return the list of file IDs for a FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        """
        ...

    @abstractmethod
    async def process_file_upload_report(
        self, *, file_upload_report: FileUploadReport
    ) -> None:
        """Use a file upload report to clean up a file from the inbox bucket and
        set the FileUpload state to 'archived'.

        Raises:
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
