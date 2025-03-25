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
#

"""Translators for publishing notification events."""

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.custom_types import JsonObject
from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from ..models.ivas import Iva
from ..ports.event_pub import EventPublisherPort

__all__ = ["EventPubTranslator", "EventPubTranslatorConfig"]


class EventPubTranslatorConfig(BaseSettings):
    """Config for the event pub translator"""

    auth_events_topic: str = Field(
        default="auth",
        description="The name of the topic for authentication related events",
    )
    second_factor_recreated_event_type: str = Field(
        default="second_factor_recreated",
        description="The event type for recreation of the second factor for authentication",
    )
    iva_state_changed_topic: str = Field(
        default="ivas",
        description="The name of the topic for IVA related events",
    )
    iva_state_changed_type: str = Field(
        default="iva_state_changed",
        description="The event type for IVA state changes",
    )


class EventPubTranslator(EventPublisherPort):
    """Translator from EventPublisherPort to EventPublisherProtocol."""

    def __init__(
        self,
        *,
        config: EventPubTranslatorConfig,
        event_publisher: EventPublisherProtocol,
    ):
        """Initialize with config and a provider of the EventPublisherProtocol."""
        self._config = config
        self._event_publisher = event_publisher

    async def publish_2fa_recreated(self, *, user_id: str) -> None:
        """Publish an event relaying that the 2nd factor of a user was recreated."""
        payload = event_schemas.UserID(
            user_id=user_id,
        ).model_dump()
        await self._event_publisher.publish(
            payload=payload,
            type_=self._config.second_factor_recreated_event_type,
            key=user_id,
            topic=self._config.auth_events_topic,
        )

    async def publish_iva_state_changed(self, *, iva: Iva) -> None:
        """Publish an event relaying that the state of a user IVA has been changed."""
        payload: JsonObject = event_schemas.UserIvaState(
            user_id=iva.user_id,
            value=iva.value,
            type=event_schemas.IvaType[iva.type.name],
            state=event_schemas.IvaState[iva.state.name],
        ).model_dump()
        await self._event_publisher.publish(
            payload=payload,
            type_=self._config.iva_state_changed_type,
            key=f"iva-{iva.id}",
            topic=self._config.iva_state_changed_topic,
        )

    async def publish_ivas_reset(self, *, user_id: str) -> None:
        """Publish an event relaying that all IVAs of the user have been reset."""
        payload = event_schemas.UserIvaState(
            user_id=user_id,
            value=None,
            type=None,
            state=event_schemas.IvaState.UNVERIFIED,
        ).model_dump()
        await self._event_publisher.publish(
            payload=payload,
            type_=self._config.iva_state_changed_type,
            key=f"all-{user_id}",
            topic=self._config.iva_state_changed_topic,
        )
