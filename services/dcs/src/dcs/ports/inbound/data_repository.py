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

"""Interface for managing and accessing DRS objects."""

from abc import ABC, abstractmethod

from ghga_service_commons.utils.multinode_storage import S3ObjectStoragesConfig

from dcs.core import models


class DataRepositoryPort(ABC):
    """A service that manages a registry of DRS objects."""

    class APICommunicationError(RuntimeError):
        """Raised when communication with external API fails due to connection issues"""

        def __init__(self, *, api_url: str):
            message = f"Failed to communicate with API at {api_url}"
            super().__init__(message)

    class CleanupError(RuntimeError):
        """
        Raised when removal of an object from the outbox could not be performed due to
        an underlying issue
        """

        def __init__(self, *, object_id: str, from_error: Exception):
            message = f"Could not remove object {
                    object_id} from outbox: {str(from_error)}"
            super().__init__(message)

    class DrsObjectNotFoundError(RuntimeError):
        """Raised when no DRS object was found with the specified DRS ID."""

        def __init__(self, *, drs_id: str):
            message = f"No DRS object with the following ID exists: {drs_id}"
            super().__init__(message)

    class EnvelopeNotFoundError(RuntimeError):
        """Raised when an envelope for a given download was not found"""

        def __init__(self, *, object_id: str):
            message = f"Envelope not found for object {object_id}"
            super().__init__(message)

    class RetryAccessLaterError(RuntimeError):
        """Raised when trying to access a DRS object that is not yet in the outbox.
        Instructs to retry later.
        """

        def __init__(self, *, retry_after: int):
            """Configure with the seconds after which a retry is should be performed."""
            self.retry_after = retry_after
            message = (
                "The requested DRS object is not yet accessible, please retry after"
                + f" {self.retry_after} seconds."
            )

            super().__init__(message)

    class StorageAliasNotConfiguredError(RuntimeError):
        """Raised when looking up an object storage configuration by alias fails."""

        def __init__(self, *, alias: str):
            message = (
                f"Could not find a storage configuration for alias {alias}.\n"
                + "Check íf your multi node configuration contains a corresponding entry."
            )
            super().__init__(message)

    class UnexpectedAPIResponseError(RuntimeError):
        """Raise when API call returns unexpected return code"""

        def __init__(self, *, api_url: str, response_code: int):
            message = f"Call to {api_url} returned unexpected response code {
                    response_code}"
            super().__init__(message)

    @abstractmethod
    async def access_drs_object(self, *, drs_id: str) -> models.DrsObjectResponseModel:
        """
        Serve the specified DRS object with access information.
        If it does not exists in the outbox, yet, a RetryAccessLaterError is raised that
        instructs to retry the call after a specified amount of time.
        """
        ...

    @abstractmethod
    async def cleanup_outbox_buckets(
        self, *, object_storages_config: S3ObjectStoragesConfig
    ):
        """Run cleanup task for all outbox buckets configured in the service config."""
        ...

    @abstractmethod
    async def cleanup_outbox(self, *, storage_alias: str):
        """
        Check if files present in the outbox have outlived their allocated time and remove
        all that do.
        For each file in the outbox, its 'last_accessed' field is checked and compared
        to the current datetime. If the threshold configured in the cache_timeout option
        is met or exceeded, the corresponding file is removed from the outbox.
        """
        ...

    @abstractmethod
    async def register_new_file(self, *, file: models.DrsObjectBase):
        """Register a file as a new DRS Object."""
        ...

    @abstractmethod
    async def serve_envelope(self, *, drs_id: str, public_key: str) -> str:
        """
        Retrieve envelope for the object with the given DRS ID

        :returns: base64 encoded envelope bytes
        """
        ...

    @abstractmethod
    async def delete_file(self, *, file_id: str) -> None:
        """Deletes a file from the outbox storage, the internal database and the
        corresponding secret from the secrets store.
        If no file or secret with that id exists, do nothing.

        Args:
            file_id: id for the file to delete.
        """
        ...
