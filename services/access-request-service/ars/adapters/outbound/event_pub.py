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

"""Translators that target the event publishing protocol."""

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.custom_types import JsonObject
from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import BaseSettings, EmailStr, Field

from ars.ports.outbound.notification_emitter import NotificationEmitterPort

__all__ = ["NotificationEmitterConfig", "NotificationEmitter"]


class NotificationEmitterConfig(BaseSettings):
    """Config for sending notification events."""

    notification_event_topic: str = Field(
        ...,
        description=("Name of the topic used for notification events."),
        example="notifications",
    )
    notification_event_type: str = Field(
        ...,
        description=("The type used for notification events."),
        example="notification",
    )


class NotificationEmitter(NotificationEmitterPort):
    """Translator from NotificationEmitterPort to EventPublisherProtocol."""

    def __init__(
        self,
        *,
        config: NotificationEmitterConfig,
        event_publisher: EventPublisherProtocol
    ):
        """Initialize with config and a provider of the EventPublisherProtocol."""
        self._event_topic = config.notification_event_topic
        self._event_type = config.notification_event_type
        self._event_publisher = event_publisher

    async def notify(
        self, *, email: EmailStr, full_name: str, subject: str, text: str
    ) -> None:
        """Send notification to the specified email address."""
        payload: JsonObject = event_schemas.Notification(
            recipient_email=email,
            recipient_name=full_name,
            subject=subject,
            plaintext_body=text,
        ).dict()

        await self._event_publisher.publish(
            payload=payload,
            type_=self._event_type,
            key=email,
            topic=self._event_topic,
        )
