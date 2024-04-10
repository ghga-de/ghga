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
#

"""Contains the implementation of the Orchestrator class"""

import logging

from nos.config import Config
from nos.core import notifications
from nos.core.models import User
from nos.ports.inbound.orchestrator import OrchestratorPort
from nos.ports.outbound.dao import ResourceNotFoundError, UserDaoPort
from nos.ports.outbound.notification_emitter import NotificationEmitterPort

log = logging.getLogger(__name__)

DATA_STEWARD_NAME = "Data Steward"


class Orchestrator(OrchestratorPort):
    """The Orchestrator class"""

    def __init__(
        self,
        *,
        config: Config,
        user_dao: UserDaoPort,
        notification_emitter: NotificationEmitterPort,
    ):
        self._config = config
        self._user_dao = user_dao
        self._notification_emitter = notification_emitter

    async def process_access_request_notification(
        self, *, event_type: str, user_id: str, dataset_id: str
    ):
        """Handle notifications for access requests.

        Raises:
            - MissingUserError:
                When the provided user ID does not exist in the DB.
        """
        method_map = {
            self._config.access_request_created_event_type: self._access_request_created,
            self._config.access_request_allowed_event_type: self._access_request_allowed,
            self._config.access_request_denied_event_type: self._access_request_denied,
        }
        extra = {  # for error logging
            "user_id": user_id,
            "dataset_id": dataset_id,
            "notification_name": "Access Request Created",
        }

        try:
            user = await self._user_dao.get_by_id(user_id)
        except ResourceNotFoundError as err:
            error = self.MissingUserError(
                user_id=user_id, notification_name=extra["notification_name"]
            )
            log.error(error, extra=extra)
            raise error from err

        await method_map[event_type](user=user, dataset_id=dataset_id)

    async def _access_request_created(self, *, user: User, dataset_id: str):
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
                dataset_id=dataset_id
            ),
        )
        log.info("Sent Access Request Created notification to data requester")

        # Send a notification to the data steward
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.ACCESS_REQUEST_CREATED_TO_DS.formatted(
                full_user_name=user.name, email=user.email, dataset_id=dataset_id
            ),
        )
        log.info("Sent Access Request Created notification to data steward")

    async def _access_request_allowed(self, *, user: User, dataset_id: str):
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
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.ACCESS_REQUEST_ALLOWED_TO_USER.formatted(
                dataset_id=dataset_id
            ),
        )
        log.info("Sent Access Request Allowed notification to data requester")

        # Send a confirmation email to the data steward
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.ACCESS_REQUEST_ALLOWED_TO_DS.formatted(
                full_user_name=user.name, dataset_id=dataset_id
            ),
        )
        log.info("Sent Access Request Allowed notification to data steward")

    async def _access_request_denied(self, *, user: User, dataset_id: str):
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
        await self._notification_emitter.notify(
            email=user.email,
            full_name=user.name,
            notification=notifications.ACCESS_REQUEST_DENIED_TO_USER.formatted(
                dataset_id=dataset_id
            ),
        )
        log.info("Sent Access Request Denied notification to data requester")

        # Send a confirmation email to the data steward
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.ACCESS_REQUEST_DENIED_TO_DS.formatted(
                full_user_name=user.name, dataset_id=dataset_id
            ),
        )
        log.info("Sent Access Request Denied notification to data steward")

    async def process_file_registered_notification(self, *, file_id: str):
        """Send notifications for internal file registrations (completed uploads)."""
        # Send an email to the data steward
        await self._notification_emitter.notify(
            email=self._config.central_data_stewardship_email,
            full_name=DATA_STEWARD_NAME,
            notification=notifications.FILE_REGISTERED_TO_DS.formatted(file_id=file_id),
        )
        log.info("Sent File Upload Completed notification to data steward")
