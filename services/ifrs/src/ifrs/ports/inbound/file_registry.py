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

"""Interface for managing a internal registry of files."""

from abc import ABC, abstractmethod

from pydantic import UUID4

from ifrs.core import models


class FileRegistryPort(ABC):
    """The interface of a service that manages a registry files stored on a permanent
    object storage.
    """

    class InvalidRequestError(RuntimeError, ABC):
        """A base for exceptions that are thrown when the request to this port was
        invalid due to a client mistake.
        """

    class FatalError(RuntimeError, ABC):
        """A base for exceptions that thrown for errors that are not a client mistake
        but likely a bug in the application. Exceptions of this kind should not be
        handled, but let the application terminate.
        """

    class FileNotInInterrogationError(InvalidRequestError):
        """Thrown when the content of a file is unexpectedly not in the staging storage."""

        def __init__(self, file_id: UUID4):
            message = (
                f"The content of the file with id '{file_id}' does not exist in the"
                + " staging storage."
            )
            super().__init__(message)

    class FileUpdateError(InvalidRequestError):
        """Thrown when attempting to update metadata of an existing file."""

        def __init__(self, file_id: UUID4):
            message = (
                f"The file with the ID '{file_id}' has already been registered and the "
                + " provided metadata is not identical to the existing one. Updates are"
                + " not permitted."
            )
            super().__init__(message)

    class ChecksumMismatchError(InvalidRequestError):
        """Thrown when the checksum of the decrypted content of a file did not match the
        expectations.
        """

        def __init__(
            self, file_id: UUID4, provided_checksum: str, expected_checksum: str
        ):
            message = (
                "The checksum of the decrypted content of the file with the ID"
                + f" '{file_id}' did not match the expectation: expected"
                + f" '{expected_checksum}' but '{provided_checksum}' was provided."
            )
            super().__init__(message)

    class SizeMismatchError(InvalidRequestError):
        """Thrown when the size of the object in storage does not match the expected size
        specified in the FileUpload object.
        """

        def __init__(self, file_id: UUID4, expected_size: int, actual_size: int):
            message = (
                f"The size of the object for file with the ID '{file_id}' does not"
                + f" match the expected size: expected {expected_size} bytes but"
                + f" actual size is {actual_size} bytes."
            )
            super().__init__(message)

    class FileNotInRegistryError(InvalidRequestError):
        """Thrown when a file is requested that has not (yet) been registered."""

        def __init__(self, file_id: UUID4):
            message = f"No file with the ID '{file_id}' has yet been registered."
            super().__init__(message)

    class FileInRegistryButNotInStorageError(FatalError):
        """Thrown if a file is registered (metadata is present in the database) but its
        content is not present in the permanent storage.
        """

        def __init__(self, file_id: UUID4):
            message = (
                f"The file with the ID '{file_id}' has been registered but its content"
                + " does not exist in the permanent object storage."
            )
            super().__init__(message)

    class CopyOperationError(FatalError):
        """Thrown if an unresolvable error occurs while copying a file between buckets."""

        def __init__(self, file_id: UUID4, dest_bucket_id: str, exc_text: str):
            message = (
                f"Fatal error occurred while copying file with the ID '{file_id}'"
                + f" to the bucket '{dest_bucket_id}'. The exception is: {exc_text}"
            )
            super().__init__(message)

    @abstractmethod
    async def register_file(self, *, file: models.ArchivableFileUpload) -> None:
        """Registers a file and moves its content from the interrogation bucket into
        permanent storage. If the file with that exact metadata has already been
        registered, nothing is done.

        Raises:
            self.FileNotInInterrogationError:
                When the file content is not present in the interrogation bucket.
            self.SizeMismatchError:
                When the file size on the received metadata doesn't match the actual
                object size in the interrogation bucket.
            ValueError:
                When the configuration for the storage alias is not found.
            self.CopyOperationError:
                When an error occurs while attempting to copy the object to the
                permanent storage bucket.
        """
        ...

    @abstractmethod
    async def stage_registered_file(
        self,
        *,
        file_id: UUID4,
        decrypted_sha256: str,
        download_object_id: UUID4,
        download_bucket_id: str,
    ) -> None:
        """Stage a registered file to the download bucket.

        Args:
            file_id:
                The unique identifier for the file that needs to be staged.
            decrypted_sha256:
                The checksum of the decrypted content. This is used to make sure that
                this service and the outside client are talking about the same file.
            download_object_id:
                The UUID4 object ID to use when copying the file to the download bucket.
            download_bucket_id:
                The S3 bucket ID for the download bucket.

        Raises:
            self.ChecksumMismatchError:
                When the provided checksum did not match the expectations.
            self.FileInRegistryButNotInStorageError:
                When encountering inconsistency between the registry (the database) and
                the permanent storage. This is an internal service error, which should
                not happen, and not the fault of the client.
            self.CopyOperationError:
                When an error occurs while attempting to copy the object to the download
                bucket.
        """
        ...

    @abstractmethod
    async def delete_file(self, *, file_id: UUID4) -> None:
        """Deletes a file from the permanent storage and the internal database.
        If no file with that ID exists, do nothing.

        Args:
            file_id:
                The unique identifier for the file that needs to be deleted.
        """
        ...

    @abstractmethod
    async def handle_file_upload(self, *, file_upload: models.FileUpload) -> None:
        """Decide what to do with a FileUpload"""
        ...
