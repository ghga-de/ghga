# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Adapter that sends SMS notifications as events"""

from pydantic import Field
from pydantic_settings import BaseSettings

from ars.ports.outbound.sms import SmsNotifierPort
from ghga_event_schemas.pydantic_ import SmsNotification
from hexkit.protocols.eventpub import EventPublisherProtocol

__all__ = ["SmsNotifier", "SmsNotifierConfig"]


class SmsNotifierConfig(BaseSettings):
    """Config for publishing SMS notification events."""

    notification_topic: str = Field(
        default=...,
        description="Name of the topic used for notification events.",
        examples=["notifications"],
    )
    sms_notification_type: str = Field(
        default=...,
        description="The type used for SMS notification events.",
        examples=["sms_notification"],
    )


class SmsNotifier(SmsNotifierPort):
    """Publishes SMS notification events, which the notification service sends."""

    def __init__(
        self, *, config: SmsNotifierConfig, event_publisher: EventPublisherProtocol
    ):
        """Initialize with config and an event publisher."""
        self._topic = config.notification_topic
        self._type = config.sms_notification_type
        self._event_publisher = event_publisher

    async def send_sms(self, *, phone: str, text: str, key: str) -> None:
        """Send the given text to the given phone number in E.164 format.

        The event is published with the given key.
        """
        payload = SmsNotification(phone=phone, text=text).model_dump()
        await self._event_publisher.publish(
            payload=payload, type_=self._type, key=key, topic=self._topic
        )
