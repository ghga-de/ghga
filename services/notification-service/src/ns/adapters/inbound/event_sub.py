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
"""Event subscriber details for notification events"""

import logging
from contextlib import suppress
from uuid import UUID

import ghga_event_schemas.pydantic_ as event_schemas
from ghga_event_schemas.configs import NotificationEventsConfig
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol

from ns.models import EventId
from ns.ports.inbound.notifier import NotifierPort
from ns.ports.outbound.dao import EventIdDaoPort, ResourceNotFoundError

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(NotificationEventsConfig):
    """Config for the event subscriber"""


class EventSubTranslator(EventSubscriberProtocol):
    """A translator that can consume Notification events"""

    def __init__(
        self,
        *,
        config: EventSubTranslatorConfig,
        notifier: NotifierPort,
        event_id_dao: EventIdDaoPort,
    ):
        self.topics_of_interest = [config.notification_topic]
        self.types_of_interest = [config.notification_type]
        self._config = config
        self._notifier = notifier
        self._event_id_dao = event_id_dao

    async def _send_notification(self, *, payload: JsonObject):
        """Validates the schema, then makes a call to the notifier with the payload"""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.Notification
        )

        await self._notifier.send_notification(notification=validated_payload)

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
        event_id: UUID,
    ) -> None:
        """Consumes an event"""
        # Don't need to check for topic and type because we only subscribe to one topic
        # and hexkit ensures that the event is of the correct type.
        with suppress(ResourceNotFoundError):
            _ = await self._event_id_dao.get_by_id(event_id)
            log.info("Notification already processed, skipping. Event_id=%s", event_id)
            return

        # Let the DLQ handle any errors that bubble up
        log.info("Processing notification. Event_id=%s", event_id)
        await self._send_notification(payload=payload)

        # If successfully processed, retain the event ID
        log.info("Notification sent successfully. Event_id=%s", event_id)
        await self._event_id_dao.insert(EventId(event_id=event_id))
