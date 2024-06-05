# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Interfaces for the main upload handling logic of this service."""

from abc import ABC, abstractmethod

from ucs.core import models
from ucs.ports.inbound.file_service import FileMetadataServicePort


class UploadServicePort(ABC):
    """Interface of a service handling uploads to the Inbox storage."""

    class FileUnknownError(FileMetadataServicePort.FileUnknownError):
        """A shortcut to the corresponding error from the FileMetadataServicePort."""

    class UnknownUploadError(RuntimeError):
        """Thrown when an upload attempt with the given ID is not known."""

        def __init__(self, *, upload_id: str):
            self.upload_id = upload_id
            message = f"The upload attempt with ID {upload_id} is unkown."
            super().__init__(message)

    class UploadStatusMismatchError(RuntimeError):
        """Thrown when an upload was expected to have a specific status for performing
        an action.
        """

        def __init__(
            self,
            *,
            upload_id: str,
            expected_status: models.UploadStatus,
            current_status: models.UploadStatus,
        ):
            self.upload_id = upload_id
            self.expected_status = expected_status
            self.current_status = current_status
            message = (
                f"The upload with ID {upload_id} must be in '{expected_status}' state to"
                + " perform the requested action, however, its current state is:"
                + str(current_status)
            )
            super().__init__(message)

    class ExistingActiveUploadError(RuntimeError):
        """Thrown when trying to create a new upload while another upload is already active."""

        def __init__(self, *, active_upload: models.UploadAttempt):
            self.active_upload = active_upload
            message = (
                "Failed to create a new multi-part upload for the file with ID"
                + f" {self.active_upload.file_id} because another upload is"
                + " currently active or has been accepted."
                + f" ID, status of the existing upload: {self.active_upload.upload_id},"
                + f" {self.active_upload.status}"
            )
            super().__init__(message)

    class UploadCompletionError(RuntimeError):
        """Thrown when the confirmation of an upload attempt failed."""

        def __init__(self, *, upload_id: str, reason: str):
            self.reason = reason
            self.upload_id = upload_id
            message = (
                f"The confirmation of the upload attempt with ID {upload_id} failed."
                + " The upload attempt was aborted and cannot be resumed. The reason was: "
                + reason
            )
            super().__init__(message)

    class UploadCancelError(RuntimeError):
        """Thrown when the cancelling of an upload attempt failed."""

        def __init__(self, *, upload_id: str):
            self.upload_id = upload_id
            self.possible_reason = (
                "An ongoing part upload might be a reason. Please complete all part uploads"
                + " and try to cancel again."
            )
            message = (
                f"Failed to cancel the multi-part upload {upload_id}."
                + self.possible_reason
            )
            super().__init__(message)

    class StorageAndDatabaseOutOfSyncError(RuntimeError):
        """Thrown when the state of the storage and the state of the database are out of
        sync.
        """

        def __init__(self, *, problem: str):
            self.problem = problem
            message = f"The object storage and the database are out of sync: {problem}"
            super().__init__(message)

    class FileAlreadyInInboxError(StorageAndDatabaseOutOfSyncError):
        """Thrown when a file is unexpectedly already in the inbox."""

        def __init__(self, *, file_id: str):
            self.file_id = file_id
            problem = f"The file with ID {file_id} is already in the inbox."
            super().__init__(problem=problem)

    class FileNotInInboxError(StorageAndDatabaseOutOfSyncError):
        """Thrown when a file is declared to be uploaded but was not found in the inbox."""

        def __init__(self, *, file_id: str):
            self.file_id = file_id
            problem = f"The file with ID {file_id} not in the inbox."
            super().__init__(problem=problem)

    class NoLatestUploadError(RuntimeError):
        """Thrown when a latest upload is expected for a file but no one was found."""

        def __init__(self, *, file_id: str):
            self.file_id = file_id
            message = f"The file with ID {file_id} as no upload."
            super().__init__(message)

    class UnknownStorageAliasError(RuntimeError):
        """Thrown when the requested storage location is not configured.
        The given parameter given should be a configured alias, but is not.
        """

        def __init__(self, *, storage_alias: str):
            self.storage_alias = storage_alias
            message = f"No storage node exists for alias {storage_alias}."
            super().__init__(message)

    @abstractmethod
    async def initiate_new(
        self, *, file_id: str, submitter_public_key: str, storage_alias: str
    ) -> models.UploadAttempt:
        """Initiates a new multi-part upload for the file with the given ID."""
        ...

    @abstractmethod
    async def get_details(self, *, upload_id: str) -> models.UploadAttempt:
        """Get details on an existing multipart upload by specifing its ID."""
        ...

    @abstractmethod
    async def create_part_url(self, *, upload_id: str, part_no: int) -> str:
        """
        Create and return a pre-signed URL to upload the bytes for the file part with
        the given number of the upload with the given ID.
        """
        ...

    @abstractmethod
    async def complete(self, *, upload_id: str) -> None:
        """Confirm the completion of the multi-part upload with the given ID."""
        ...

    @abstractmethod
    async def cancel(self, *, upload_id: str) -> None:
        """Cancel the multi-part upload with the given ID."""
        ...

    @abstractmethod
    async def accept_latest(self, *, file_id: str) -> None:
        """
        Accept the latest multi-part upload for the given file.

        Here the file ID is used, as this method is triggered by downstream services
        that only know the file ID not the upload attempt.
        """
        ...

    @abstractmethod
    async def reject_latest(self, *, file_id: str) -> None:
        """
        Reject the latest multi-part upload for the given file.

        Here the file ID is used, as this method is triggered by downstream services
        that only know the file ID not the upload attempt.
        """
        ...

    @abstractmethod
    async def deletion_requested(self, *, file_id: str) -> None:
        """
        Cancel the current upload attempt for the given file and remove all associated
        data related to upload attempts and file metadata.
        """
        ...
