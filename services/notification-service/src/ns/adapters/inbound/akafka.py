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

import ghga_event_schemas.pydantic_ as event_schemas
from ghga_event_schemas.configs import NotificationEventsConfig
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol

from ns.ports.inbound.notifier import NotifierPort


class EventSubTranslatorConfig(NotificationEventsConfig):
    """Config for the event subscriber"""


class EventSubTranslator(EventSubscriberProtocol):
    """A translator that can consume Notification events"""

    def __init__(self, *, config: EventSubTranslatorConfig, notifier: NotifierPort):
        self.topics_of_interest = [config.notification_topic]
        self.types_of_interest = [config.notification_type]
        self._config = config
        self._notifier = notifier

    async def _send_notification(self, *, payload: JsonObject):
        """Validates the schema, then makes a call to the notifier with the payload"""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.Notification
        )
        await self._notifier.send_notification(notification=validated_payload)

    async def _consume_validated(
        self, *, payload: JsonObject, type_: Ascii, topic: Ascii, key: Ascii
    ) -> None:
        """Consumes an event"""
        if (
            type_ == self._config.notification_type
            and topic == self._config.notification_topic
        ):
            await self._send_notification(payload=payload)
