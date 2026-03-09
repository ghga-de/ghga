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

"""Interface for managing and accessing DRS objects."""

from abc import ABC, abstractmethod

from pydantic import UUID4

from dcs.core import models


class DataRepositoryPort(ABC):
    """A service that manages a registry of DRS objects."""

    class APICommunicationError(RuntimeError):
        """Raised when communication with external API fails due to connection issues"""

        def __init__(self):
            super().__init__("Failed to communicate with the Secrets API")

    class DrsObjectNotFoundError(RuntimeError):
        """Raised when no DRS object was found corresponding to the given file ID."""

        def __init__(self, *, file_id: UUID4):
            message = f"No DRS object corresponding to the following file ID exists: {file_id}"
            super().__init__(message)

    class EnvelopeNotFoundError(RuntimeError):
        """Raised when an envelope for a given download was not found"""

        def __init__(self, *, file_id: UUID4):
            message = f"Envelope not found for file {file_id}."
            super().__init__(message)

    class RetryAccessLaterError(RuntimeError):
        """Raised when trying to access a DRS object that is not yet in the download bucket.
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

    class UnexpectedAPIResponseError(RuntimeError):
        """Raise when API call returns unexpected return code"""

        def __init__(self, *, api_url: str, response_code: int):
            message = (
                f"Call to {api_url} returned unexpected response code {response_code}"
            )
            super().__init__(message)

    @abstractmethod
    async def access_drs_object(
        self, *, accession: str, file_id: UUID4
    ) -> models.DrsObjectResponseModel:
        """
        Serve the specified DRS object with access information.
        If it does not exists in the download bucket, yet, a RetryAccessLaterError
        is raised that instructs to retry the call after a specified amount of time.
        """

    @abstractmethod
    async def register_new_file(self, *, file: models.DrsObjectBase):
        """Register a file as a new DRS Object."""

    @abstractmethod
    async def serve_envelope(self, *, file_id: UUID4, public_key: str) -> str:
        """
        Retrieve envelope for the object with the given DRS ID

        :returns: base64 encoded envelope bytes
        """

    @abstractmethod
    async def delete_file(self, *, file_id: UUID4) -> None:
        """Delete a file from the download bucket and database, and the corresponding
        secret from the secrets store. If no file or secret with that id exists,
        does nothing.

        Args:
            file_id: The UUID4 used to identify the file to delete.
        """
