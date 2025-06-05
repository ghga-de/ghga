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

"""Contains the implementation of the Orchestrator class"""

import logging
from collections.abc import Callable
from contextlib import suppress
from functools import partial

from ghga_event_schemas import pydantic_ as event_schemas

from nos.config import Config
from nos.core import notifications
from nos.ports.inbound.orchestrator import OrchestratorPort
from nos.ports.outbound.dao import (
    AccessRequestDaoPort,
    ResourceNotFoundError,
    UserDaoPort,
)
from nos.ports.outbound.notification_emitter import NotificationEmitterPort

log = logging.getLogger(__name__)

DATA_STEWARD_NAME = "Data Steward"


class Orchestrator(OrchestratorPort):
    """The Orchestrator class"""

    def __init__(
        self,
        *,
        config: Config,
        access_request_dao: AccessRequestDaoPort,
        user_dao: UserDaoPort,
        notification_emitter: NotificationEmitterPort,
    ):
        self._config = config
        self._user_dao = user_dao
        self._access_request_dao = access_request_dao
        self._notification_emitter = notification_emitter

    async def _process_access_request_notification(
        self, *, access_request: event_schemas.AccessRequestDetails
    ):
        """Handle notifications for access requests.

        Raises:
            - MissingUserError:
                When the provided user ID does not exist in the DB.
        """
        user_id = access_request.user_id
        dataset_id = access_request.dataset_id
        status = access_request.status
        event_type_assets: dict[str, tuple[str, Callable]] = {
            event_schemas.AccessRequestStatus.PENDING.value: (
                "Access Request Created",
                self._access_request_created,
            ),
            event_schemas.AccessRequestStatus.ALLOWED.value: (
                "Access Request Allowed",
                self._access_request_allowed,
            ),
            event_schemas.AccessRequestStatus.DENIED.value: (
                "Access Request Denied",
                self._access_request_denied,
            ),
        }
        notification_name, handler = event_type_assets[status]
        extra = {  # for error logging
            "user_id": user_id,
            "dataset_id": dataset_id,
            "notification_name": notification_name,
        }

        try:
            user = await self._user_dao.get_by_id(user_id)
        except ResourceNotFoundError as err:
            error = self.MissingUserError(
                user_id=user_id, notification_name=extra["notification_name"]
            )
            log.error(error, extra=extra)
            raise error from err

        await handler(user=user, access_request=access_request)

    async def _access_request_created(
        self,
        *,
        user: event_schemas.User,
        access_request: event_schemas.AccessRequestDetails,
    ):
        """Processes an Access Request Created event.

        One notification is sent to the data requester to confirm that their request
        was created.

        Another notification is sent to the data steward to inform them of the request.

        Raises:
            - NotificationInterpolationError:
                When there is a problem with the values used to perform the notification
                text interpolation.
        """
        # Send a confirmation email notification to the Data Requester
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.ACCESS_REQUEST_CREATED_TO_USER.formatted(
                dataset_id=access_request.dataset_id
            ),
        )
        log.info("Sent Access Request Created notification to data requester")

        # Send a notification to the data steward
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.ACCESS_REQUEST_CREATED_TO_DS.formatted(
                full_user_name=user.name,
                email=user.email,
                dataset_id=access_request.dataset_id,
                dataset_title=access_request.dataset_title,
                dac_alias=access_request.dac_alias,
                dac_email=access_request.dac_email,
                request_text=access_request.request_text,
            ),
        )
        log.info("Sent Access Request Created notification to data steward")

    async def _access_request_allowed(
        self,
        *,
        user: event_schemas.User,
        access_request: event_schemas.AccessRequestDetails,
    ):
        """Process an Access Request Allowed event.

        One notification is sent to the data requester to inform them that the request
        has been approved/allowed.

        Another notification is sent to the data steward confirming that the request
        was allowed.

        Raises:
            - NotificationInterpolationError:
                When there is a problem with the values used to perform the notification
                text interpolation.
        """
        # Send a notification to the data requester
        note_to_requester = (
            (
                "\nThe Data Steward has also included the following note:\n"
                + access_request.note_to_requester
            )
            if access_request.note_to_requester
            else ""
        )

        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.ACCESS_REQUEST_ALLOWED_TO_USER.formatted(
                dataset_id=access_request.dataset_id,
                note_to_requester=note_to_requester,
            ),
        )
        log.info("Sent Access Request Allowed notification to data requester")

        # Send a confirmation email to the data steward
        ticket_id = access_request.ticket_id
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.ACCESS_REQUEST_ALLOWED_TO_DS.formatted(
                full_user_name=user.name,
                dataset_id=access_request.dataset_id,
                ticket_id=f"#{ticket_id}" if ticket_id else "Missing",
            ),
        )
        log.info("Sent Access Request Allowed notification to data steward")

    async def _access_request_denied(
        self,
        *,
        user: event_schemas.User,
        access_request: event_schemas.AccessRequestDetails,
    ):
        """Process an Access Request Denied event.

        One notification is sent to the data requester telling them that the request
        was denied.

        Another confirmation notification is sent to the data steward.

        Raises:
            - NotificationInterpolationError:
                When there is a problem with the values used to perform the notification
                text interpolation.
        """
        # Send a notification to the data requester
        note_to_requester = (
            (
                "\nThe Data Steward has also included the following note:\n"
                + access_request.note_to_requester
            )
            if access_request.note_to_requester
            else ""
        )

        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.ACCESS_REQUEST_DENIED_TO_USER.formatted(
                dataset_id=access_request.dataset_id,
                note_to_requester=note_to_requester,
            ),
        )
        log.info("Sent Access Request Denied notification to data requester")

        # Send a confirmation email to the data steward
        ticket_id = access_request.ticket_id
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.ACCESS_REQUEST_DENIED_TO_DS.formatted(
                full_user_name=user.name,
                dataset_id=access_request.dataset_id,
                ticket_id=f"#{ticket_id}" if ticket_id else "Missing",
            ),
        )
        log.info("Sent Access Request Denied notification to data steward")

    async def _iva_code_requested(self, *, user: event_schemas.User):
        """Send notifications relaying that an IVA code has been requested.

        One notification is sent to the user to confirm that their request was received.

        Another notification is sent to the data steward to inform them of the request.
        """
        # Send a notification to the user
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.IVA_CODE_REQUESTED_TO_USER,
        )

        # Send a notification to the data steward
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.IVA_CODE_REQUESTED_TO_DS.formatted(
                full_user_name=user.name, email=user.email
            ),
        )

    async def _iva_code_transmitted(self, *, user: event_schemas.User):
        """Send a notification that an IVA code has been transmitted to the user."""
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.IVA_CODE_TRANSMITTED_TO_USER,
        )

    async def _iva_code_validated(self, *, user: event_schemas.User):
        """Send a notification to the data steward that an IVA code has been validated."""
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.IVA_CODE_SUBMITTED_TO_DS.formatted(
                full_user_name=user.name, email=user.email
            ),
        )

    async def _iva_unverified(
        self,
        *,
        iva_type: str,
        user: event_schemas.User,
    ):
        """Send notifications for IVAs set to 'unverified'.

        This usually happens when the user exceeds the allotted time to submit their IVA
        code or exhausts all the allotted verification attempts.
        """
        # send a notification to the user
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.IVA_UNVERIFIED_TO_USER.formatted(
                helpdesk_email=self._config.helpdesk_email
            ),
        )

        # send a notification to the data steward
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.IVA_UNVERIFIED_TO_DS.formatted(
                full_user_name=user.name, email=user.email, type=iva_type
            ),
        )

    async def process_all_ivas_invalidated(self, *, user_id: str):
        """Send a notification to the user when all their IVAs are reset."""
        try:
            user = await self._user_dao.get_by_id(user_id)
        except ResourceNotFoundError as err:
            error = self.MissingUserError(
                user_id=user_id, notification_name="All IVAs Invalidated"
            )
            log.error(
                error,
                extra={"user_id": user_id, "notification_name": "All IVAs Invalidated"},
            )
            raise error from err

        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.ALL_IVAS_INVALIDATED_TO_USER.formatted(
                helpdesk_email=self._config.helpdesk_email
            ),
        )

    async def process_iva_state_change(self, *, user_iva: event_schemas.UserIvaState):
        """Handle notifications for IVA state changes."""
        # Map IVA states to their corresponding notification methods and a name for logs
        method_map: dict[event_schemas.IvaState, tuple[Callable, str]] = {
            event_schemas.IvaState.CODE_REQUESTED: (
                self._iva_code_requested,
                "IVA Code Requested",
            ),
            event_schemas.IvaState.CODE_TRANSMITTED: (
                self._iva_code_transmitted,
                "IVA Code Transmitted",
            ),
            event_schemas.IvaState.VERIFIED: (
                self._iva_code_validated,
                "IVA Code Validated",
            ),
            event_schemas.IvaState.UNVERIFIED: (
                partial(
                    self._iva_unverified,
                    iva_type=user_iva.type.value.lower() if user_iva.type else "N/A",
                ),
                "IVA Unverified",
            ),
        }

        if user_iva.state not in method_map:
            unexpected_iva_state_error = self.UnexpectedIvaState(state=user_iva.state)
            log.error(
                unexpected_iva_state_error,
                extra={
                    "user_id": user_iva.user_id,
                },
            )
            raise unexpected_iva_state_error

        extra = {
            "user_id": user_iva.user_id,
            "notification_name": method_map[user_iva.state][1],
        }

        try:
            user = await self._user_dao.get_by_id(user_iva.user_id)
        except ResourceNotFoundError as err:
            error = self.MissingUserError(
                user_id=user_iva.user_id, notification_name=extra["notification_name"]
            )
            log.error(error, extra=extra)
            raise error from err

        await method_map[user_iva.state][0](user=user)

    def _changed_info(
        self, existing_user: event_schemas.User, new_user: event_schemas.User
    ) -> str:
        """Check what critical user information has changed (if any).

        Critical information includes the user's email address and name.
        """
        changed = []
        for field in ["email", "name"]:
            if getattr(existing_user, field) != getattr(new_user, field):
                changed.append(field)
        return " and ".join(changed)

    async def upsert_access_request(
        self, *, access_request: event_schemas.AccessRequestDetails
    ) -> None:
        """Upsert an access request object and send out the appropriate notification."""
        # Publish a notification under two circumstances:
        # 1. We're seeing the notification for the first time
        # 2. We have a record of the request, but the inbound event's status differs
        should_notify = True
        with suppress(ResourceNotFoundError):
            existing_request = await self._access_request_dao.get_by_id(
                access_request.id
            )
            should_notify = existing_request.status != access_request.status

        if should_notify:
            await self._process_access_request_notification(
                access_request=access_request
            )

        await self._access_request_dao.upsert(access_request)

    async def delete_access_request(self, *, resource_id: str) -> None:
        """Delete an access request object."""
        with suppress(ResourceNotFoundError):
            await self._access_request_dao.delete(resource_id)

    async def upsert_user_data(
        self, resource_id: str, update: event_schemas.User
    ) -> None:
        """Upsert the user data.

        This method will also examine the user data and send out notifications for
        user re-registration.
        """
        with suppress(ResourceNotFoundError):
            existing_user = await self._user_dao.get_by_id(resource_id)
            if changed_details := self._changed_info(existing_user, update):
                await self._notification_emitter.notify(
                    email=existing_user.email,
                    full_name=update.name,
                    notification=notifications.USER_REREGISTERED_TO_USER.formatted(
                        helpdesk_email=self._config.helpdesk_email,
                        changed_details=changed_details,
                    ),
                )
                log.info("Sent User Re-registered notification to user")
        await self._user_dao.upsert(dto=update)

    async def delete_user_data(self, resource_id: str) -> None:
        """Delete the user data.

        In the case that the user ID does not exist in the database, this method will
        log the fact but not raise an error.
        """
        try:
            await self._user_dao.delete(resource_id)
        except ResourceNotFoundError:
            # do not raise an error if the user is not found, just log it.
            log.warning("User not found for deletion", extra={"user_id": resource_id})

    async def process_second_factor_recreated(self, *, user_id: str) -> None:
        """Send a notification to the user that their second factor has been recreated."""
        try:
            user = await self._user_dao.get_by_id(user_id)
        except ResourceNotFoundError as err:
            error = self.MissingUserError(
                user_id=user_id, notification_name="Second Factor Recreated"
            )
            log.error(
                error,
                extra={
                    "user_id": user_id,
                    "notification_name": "Second Factor Recreated",
                },
            )
            raise error from err

        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.SECOND_FACTOR_RECREATED_TO_USER.formatted(
                helpdesk_email=self._config.helpdesk_email
            ),
        )
