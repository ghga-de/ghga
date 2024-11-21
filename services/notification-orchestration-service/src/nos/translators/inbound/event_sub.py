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
"""Event subscriber definition."""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from nos.ports.inbound.orchestrator import OrchestratorPort


class EventSubTranslatorConfig(BaseSettings):
    """Config for the event subscriber"""

    access_request_events_topic: str = Field(
        default=...,
        description="Name of the event topic used to consume access request events",
        examples=["access_requests"],
    )
    access_request_created_event_type: str = Field(
        default=...,
        description="The type to use for access request created events",
        examples=["access_request_created"],
    )
    access_request_allowed_event_type: str = Field(
        default=...,
        description="The type to use for access request allowed events",
        examples=["access_request_allowed"],
    )
    access_request_denied_event_type: str = Field(
        default=...,
        description="The type to use for access request denied events",
        examples=["access_request_denied"],
    )
    iva_state_changed_event_topic: str = Field(
        default=...,
        description="The name of the topic containing IVA events.",
        examples=["ivas"],
    )
    iva_state_changed_event_type: str = Field(
        default=...,
        description="The type to use for iva state changed events.",
        examples=["iva_state_changed"],
    )
    second_factor_recreated_event_topic: str = Field(
        default=...,
        description="The name of the topic containing second factor recreation events.",
        examples=["auth"],
    )
    second_factor_recreated_event_type: str = Field(
        default=...,
        description="The event type for recreation of the second factor for authentication",
        examples=["second_factor_recreated"],
    )


class EventSubTranslator(EventSubscriberProtocol):
    """A translator that can consume events"""

    def __init__(
        self, *, config: EventSubTranslatorConfig, orchestrator: OrchestratorPort
    ):
        self.topics_of_interest = [
            config.access_request_events_topic,
            config.iva_state_changed_event_topic,
            config.second_factor_recreated_event_topic,
        ]
        self.types_of_interest = [
            config.access_request_created_event_type,
            config.access_request_allowed_event_type,
            config.access_request_denied_event_type,
            config.iva_state_changed_event_type,
            config.second_factor_recreated_event_type,
        ]
        self._config = config
        self._orchestrator = orchestrator

    async def _handle_access_request(self, type_: str, payload: JsonObject) -> None:
        """Send notifications for an access request-related event."""
        validated_payload = get_validated_payload(
            payload, event_schemas.AccessRequestDetails
        )
        await self._orchestrator.process_access_request_notification(
            event_type=type_,
            user_id=validated_payload.user_id,
            dataset_id=validated_payload.dataset_id,
        )

    async def _handle_iva_state_change(self, payload: JsonObject) -> None:
        """Send notifications for IVA state changes."""
        validated_payload = get_validated_payload(payload, event_schemas.UserIvaState)
        await self._orchestrator.process_iva_state_change(user_iva=validated_payload)

    async def _handle_all_ivas_reset(self, payload: JsonObject) -> None:
        """Send notifications for all IVA resets."""
        validated_payload = get_validated_payload(payload, event_schemas.UserIvaState)
        await self._orchestrator.process_all_ivas_invalidated(
            user_id=validated_payload.user_id
        )

    async def _handle_second_factor_recreated(self, payload: JsonObject) -> None:
        """Send notifications for second factor recreation."""
        validated_payload = get_validated_payload(payload, event_schemas.UserID)
        await self._orchestrator.process_second_factor_recreated(
            user_id=validated_payload.user_id
        )

    async def _consume_validated(
        self, *, payload: JsonObject, type_: Ascii, topic: Ascii, key: Ascii
    ) -> None:
        """Consumes an event"""
        match type_:
            case _ if type_ in (
                self._config.access_request_created_event_type,
                self._config.access_request_allowed_event_type,
                self._config.access_request_denied_event_type,
            ):
                await self._handle_access_request(type_, payload)
            case self._config.iva_state_changed_event_type:
                if key.startswith("all-"):
                    await self._handle_all_ivas_reset(payload=payload)
                else:
                    await self._handle_iva_state_change(payload=payload)
            case self._config.second_factor_recreated_event_type:
                await self._handle_second_factor_recreated(payload=payload)


class OutboxSubTranslatorConfig(BaseSettings):
    """Config for the outbox subscriber"""

    user_events_topic: str = Field(
        default="users",
        description="The name of the topic containing user events.",
    )


class OutboxSubTranslator(DaoSubscriberProtocol[event_schemas.User]):
    """A class that consumes events conveying changes in DB resources."""

    event_topic: str
    dto_model = event_schemas.User

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        orchestrator: OrchestratorPort,
    ):
        self._config = config
        self._orchestrator = orchestrator
        self.event_topic = config.user_events_topic

    async def changed(self, resource_id: str, update: event_schemas.User) -> None:
        """Consume change event (created or updated) for user data."""
        await self._orchestrator.upsert_user_data(
            resource_id=resource_id, update=update
        )

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the deletion of a user."""
        await self._orchestrator.delete_user_data(resource_id=resource_id)
