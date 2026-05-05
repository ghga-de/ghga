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

from ghga_event_schemas.pydantic_ import (
    FileInternallyRegistered,
    InterrogationFailure,
    InterrogationSuccess,
    UploadBoxState,
)
from pydantic import UUID4

from ucs.core.models import FileUpload


class UploadControllerPort(ABC):
    """A class for managing file uploads"""

    class UploadError(RuntimeError):
        """Base error class for all upload errors"""

    class IncompleteUploadsError(UploadError):
        """Raised when trying to lock or archive a FileUploadBox for which
        at least one incomplete FileUpload exists.
        """

        def __init__(self, *, box_id: UUID4, file_ids: list[UUID4]):
            msg = (
                f"Cannot lock or archive box {box_id} because these"
                + f" files are incomplete: {file_ids}"
            )
            super().__init__(msg)

    class FileArchivalError(UploadError):
        """Raised when there's a problem that prevents archiving a given FileUpload."""

    class UnknownStorageAliasError(UploadError):
        """Raised when the requested storage alias is not configured."""

        def __init__(self, *, storage_alias: str):
            msg = f"No storage node exists for alias {storage_alias}."
            super().__init__(msg)

    class UploadAlreadyInProgressError(UploadError):
        """Raised when a file upload is initiated but one is already in progress."""

        def __init__(self, *, file_id: UUID4, bucket_id: str):
            msg = (
                f"An upload is already in progress for file ID {file_id} in"
                + f" bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class UploadSessionNotFoundError(UploadError):
        """Raised when the tracked upload session can no longer be found."""

        def __init__(self, *, bucket_id: str, s3_upload_id: str):
            msg = (
                f"Upload session with ID {s3_upload_id} could not be found in"
                + f" bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class UploadCompletionError(UploadError):
        """Raised when completing a file upload results in an error."""

        def __init__(self, *, file_id: UUID4, s3_upload_id: str, bucket_id: str):
            msg = (
                f"Failed to complete upload session {s3_upload_id} for"
                + f" file ID {file_id} in bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class UploadAbortError(UploadError):
        """Raised when aborting a file upload results in an error."""

        def __init__(self, *, file_id: UUID4, s3_upload_id: str, bucket_id: str):
            msg = (
                f"Failed to abort upload session {s3_upload_id} for"
                + f" file ID {file_id} in bucket ID {bucket_id}."
            )
            super().__init__(msg)

    class BoxVersionError(UploadError):
        """Raised when the supplied box version doesn't match the current version in the DB."""

        def __init__(self, *, box_id: UUID4):
            msg = f"The supplied version for FileUploadBox {box_id} is outdated."
            super().__init__(msg)

    class BoxStateError(UploadError):
        """Thrown when the user requests an action FileUploadBox prevented by the box's state."""

        box_state: UploadBoxState

        def __init__(self, *, box_id: UUID4, box_state: UploadBoxState):
            self.box_state = box_state
            msg = (
                "Can't perform this action because FileUploadBox with"
                + f" ID {box_id} is {box_state}"
            )
            super().__init__(msg)

    class BoxMaxSizeTooLowError(UploadError):
        """Raised when the requested max_size is less than the box's current committed size."""

        def __init__(self, *, box_id: UUID4, max_size: int, current_size: int):
            self.max_size = max_size
            self.current_size = current_size
            msg = (
                f"Cannot set max_size to {max_size} for box {box_id} because"
                f" {current_size} bytes are already committed."
            )
            super().__init__(msg)

    class BoxMaxSizeExceededError(UploadError):
        """Raised when adding a new FileUpload would exceed the box's total size limit."""

        def __init__(self, *, box_id: UUID4, max_size: int, current_size: int):
            self.max_size = max_size
            self.current_size = current_size

            msg = (
                f"Adding this file to box {box_id} would exceed the box's"
                " maximum total size limit."
            )
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

    class FileUploadStateError(UploadError):
        """Raised when a FileUpload's details don't match the expected values."""

        def __init__(self, *, file_id: UUID4, details: str):
            msg = (
                f"FileUpload with ID {file_id} doesn't match the expected state."
                + f" Details: {details}"
            )
            super().__init__(msg)

    class ChecksumMismatchError(RuntimeError):
        """Raised when the user-supplied encrypted checksum doesn't match S3."""

        def __init__(self, *, file_id: UUID4):
            msg = (
                f"The MD5 checksum supplied for the encrypted file content of {file_id}"
                + " doesn't match the value calculated by S3."
            )
            super().__init__(msg)

    @abstractmethod
    async def initiate_file_upload(
        self,
        *,
        box_id: UUID4,
        alias: str,
        decrypted_size: int,
        encrypted_size: int,
        part_size: int,
    ) -> tuple[UUID4, str]:
        """Initialize a new multipart upload.

        Returns the file ID and storage alias as a 2-tuple.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `BoxStateError` if the box exists but is locked.
        - `BoxMaxSizeExceededError` if adding the file would exceed the box's size limit.
        - `FileUploadAlreadyExists` if there's already a FileUpload for this alias.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAlreadyInProgressError` if an upload is already in progress.
        """
        ...

    @abstractmethod
    async def get_part_upload_url(self, *, file_id: UUID4, part_no: int) -> str:
        """
        Create and return a pre-signed URL to upload the bytes for the file part with
        the given number of the upload with the given file ID.

        Raises:
        - `FileUploadNotFound` if the FileUpload is not found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadSessionNotFoundError` if the upload session can't be found.
        """
        ...

    @abstractmethod
    async def complete_file_upload(  # noqa: PLR0913
        self,
        *,
        box_id: UUID4,
        file_id: UUID4,
        unencrypted_checksum: str,
        encrypted_checksum: str,
        encrypted_parts_md5: list[str],
        encrypted_parts_sha256: list[str],
    ) -> None:
        """Instruct S3 to complete a multipart upload and compares the remote checksum
        with the value provided for `encrypted_checksum`. The `unencrypted_checksum`
        is stored in the database.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `BoxNotFoundError` if the FileUploadBox isn't found.
        - `BoxStateError` if the box exists but is locked.
        - `BoxVersionError` if the box version changed before stats could be updated.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadCompletionError` if there's an error while telling S3 to complete the upload.
        - `ChecksumMismatchError` if the checksums don't match.
        """
        ...

    @abstractmethod
    async def remove_file_upload(self, *, box_id: UUID4, file_id: UUID4) -> None:
        """Remove a file upload and cancel the ongoing upload if applicable.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `BoxStateError` if the box exists but is locked.
        - `BoxVersionError` if the box version changed before stats could be updated.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        ...

    @abstractmethod
    async def create_file_upload_box(
        self, *, storage_alias: str, max_size: int
    ) -> UUID4:
        """Create a new FileUploadBox with the given S3 storage alias.
        Returns the UUID4 id of the created FileUploadBox.

        Args:
        - `storage_alias`: The S3 storage alias for uploads within this box.
        - `max_size`: The maximum total bytes allowed across all in-progress uploads.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        """
        ...

    @abstractmethod
    async def update_box_max_size(
        self, *, box_id: UUID4, version: int, max_size: int
    ) -> None:
        """Update the max_size of an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `BoxMaxSizeTooLowError` if the new max_size is smaller than what has
            already been uploaded.
        """
        ...

    @abstractmethod
    async def lock_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Lock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `IncompleteUploadsError` if the FileUploadBox has incomplete FileUploads.
        """
        ...

    @abstractmethod
    async def unlock_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Unlock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `BoxStateError` if the box is archived and cannot be unlocked.
        """
        ...

    @abstractmethod
    async def archive_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Archive an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `BoxStateError` if the box is open.
        - `IncompleteUploadsError` if the FileUploadBox has incomplete FileUploads.
        - `FileArchivalError` if there's a problem archiving a given FileUpload.
        """
        ...

    @abstractmethod
    async def get_box_file_info(self, *, box_id: UUID4) -> list[FileUpload]:
        """Return the list of FileUploads for a FileUploadBox, sorted by alias.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        """
        ...

    @abstractmethod
    async def process_interrogation_success(
        self, *, report: InterrogationSuccess
    ) -> None:
        """Update a FileUpload with the information from a corresponding successful
        interrogation report and remove it from the inbox bucket.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        ...

    @abstractmethod
    async def process_interrogation_failure(
        self, *, report: InterrogationFailure
    ) -> None:
        """Update a FileUpload state to 'failed' and remove it from the inbox bucket.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        ...

    @abstractmethod
    async def process_internal_file_registration(
        self, *, registration_metadata: FileInternallyRegistered
    ) -> None:
        """Update a FileUpload state to 'archived' and verify other data.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `FileUploadStateError` if the FileUpload's details aren't what's expected.
        """
        ...

    @abstractmethod
    async def process_file_deletion_requested(self, *, file_id: UUID4) -> None:
        """Process a deletion request for the given FileUpload ID.

        This will remove the object from the inbox, if it exists.
        Database objects are untouched.

        If no FileUpload with the given ID exists, merely logs a warning and returns.
        """
        ...
