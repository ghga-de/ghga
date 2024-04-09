# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

    class FileContentNotInStagingError(InvalidRequestError):
        """Thrown when the content of a file is unexpectedly not in the staging storage."""

        def __init__(self, file_id: str):
            message = (
                f"The content of the file with id '{file_id}' does not exist in the"
                + " staging storage."
            )
            super().__init__(message)

    class FileUpdateError(InvalidRequestError):
        """Thrown when attempting to update metadata of an existing file."""

        def __init__(self, file_id: str):
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
            self, file_id: str, provided_checksum: str, expected_checksum: str
        ):
            message = (
                "The checksum of the decrypted content of the file with the ID"
                + f" '{file_id}' did not match the expectation: expected"
                + f" '{expected_checksum}' but '{provided_checksum}' was provided."
            )
            super().__init__(message)

    class FileNotInRegistryError(InvalidRequestError):
        """Thrown when a file is requested that has not (yet) been registered."""

        def __init__(self, file_id: str):
            message = f"The file with the ID '{file_id}' has not (yet) been registered."
            super().__init__(message)

    class FileInRegistryButNotInStorageError(FatalError):
        """Thrown if a file is registered (metadata is present in the database) but its
        content is not present in the permanent storage.
        """

        def __init__(self, file_id: str):
            message = (
                f"The file with the ID '{file_id}' has been registered but its content"
                + " does not exist in the permanent object storage."
            )
            super().__init__(message)

    @abstractmethod
    async def register_file(
        self,
        *,
        file_without_object_id: models.FileMetadataBase,
        staging_object_id: str,
        staging_bucket_id: str,
    ) -> None:
        """Registers a file and moves its content from the staging into the permanent
        storage. If the file with that exact metadata has already been registered,
        nothing is done.

        Args:
            file_without_object_id: metadata on the file to register.
            staging_object_id:
                The S3 object ID for the staging bucket.
            staging_bucket_id:
                The S3 bucket ID for staging.

        Raises:
            self.FileContentNotInStagingError:
                When the file content is not present in the storage staging.
        """
        ...

    @abstractmethod
    async def stage_registered_file(
        self,
        *,
        file_id: str,
        decrypted_sha256: str,
        outbox_object_id: str,
        outbox_bucket_id: str,
    ) -> None:
        """Stage a registered file to the outbox.

        Args:
            file_id:
                The identifier of the file.
            decrypted_sha256:
                The checksum of the decrypted content. This is used to make sure that
                this service and the outside client are talking about the same file.
            outbox_object_id:
                The S3 object ID for the outbox bucket.
            outbox_bucket_id:
                The S3 bucket ID for the outbox.

        Raises:
            self.FileNotInRegistryError:
                When a file is requested that has not (yet) been registered.
            self.ChecksumMismatchError:
                When the provided checksum did not match the expectations.
            self.FileInRegistryButNotInStorageError:
                When encountering inconsistency between the registry (the database) and
                the permanent storage. This a fatal error.
        """
        ...

    @abstractmethod
    async def delete_file(self, *, file_id: str) -> None:
        """Deletes a file from the permanent storage and the internal database.
        If no file with that id exists, do nothing.

        Args:
            file_id:
                id for the file to delete.
        """
        ...
