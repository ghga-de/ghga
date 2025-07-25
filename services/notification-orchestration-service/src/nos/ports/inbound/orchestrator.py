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
#

"""Contains the definition of the Orchestrator class"""

from abc import ABC, abstractmethod

from ghga_event_schemas import pydantic_ as event_schemas
from pydantic import UUID4


class OrchestratorPort(ABC):
    """A class that creates notification events from incoming event data."""

    class MissingUserError(RuntimeError):
        """Raised when a user is not found in the database.

        The notification title is included to aid in debugging.
        """

        def __init__(self, *, user_id: UUID4, notification_name: str) -> None:
            message = (
                f"Unable to publish '{notification_name}' notification as user ID"
                + f" {user_id!r} was not found in the database."
            )
            super().__init__(message)

    class UnexpectedIvaState(RuntimeError):
        """Raised when an unexpected IVA state is encountered."""

        def __init__(self, *, state: str) -> None:
            message = f"Unexpected IVA state '{state}' encountered."
            super().__init__(message)

    @abstractmethod
    async def _process_access_request_notification(
        self, *, access_request: event_schemas.AccessRequestDetails
    ):
        """Handle notifications for access requests.

        Raises:
            - MissingUserError:
                When the provided user ID does not exist in the DB.
        """

    @abstractmethod
    async def process_all_ivas_invalidated(self, *, user_id: UUID4):
        """Send a notification to the user when all their IVAs are reset."""

    @abstractmethod
    async def process_iva_state_change(self, *, user_iva: event_schemas.UserIvaState):
        """Handle notifications for IVA state changes."""

    @abstractmethod
    async def upsert_access_request(
        self, *, access_request: event_schemas.AccessRequestDetails
    ) -> None:
        """Upsert an access request object and send out the appropriate notification."""

    @abstractmethod
    async def delete_access_request(self, *, access_request_id: UUID4) -> None:
        """Delete an access request object."""

    @abstractmethod
    async def upsert_user_data(self, update: event_schemas.User) -> None:
        """Upsert the user data.

        This method will also examine the user data and send out notifications for
        user re-registration.
        """

    @abstractmethod
    async def delete_user_data(self, user_id: UUID4) -> None:
        """Delete the user data.

        In the case that the user ID does not exist in the database, this method will
        log the fact but not raise an error.
        """

    @abstractmethod
    async def process_second_factor_recreated(self, *, user_id: UUID4) -> None:
        """Send a notification to the user that their second factor has been recreated."""
