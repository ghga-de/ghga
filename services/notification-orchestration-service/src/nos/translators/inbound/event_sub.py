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
"""Event subscriber definition."""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import UserEventsConfig
from ghga_event_schemas.configs.stateful import AccessRequestEventsConfig
from ghga_event_schemas.configs.stateless import (
    IvaChangeEventsConfig,
    SecondFactorRecreatedEventsConfig,
)
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.protocols.eventsub import EventSubscriberProtocol

from nos.ports.inbound.orchestrator import OrchestratorPort


class EventSubTranslatorConfig(
    IvaChangeEventsConfig, SecondFactorRecreatedEventsConfig
):
    """Config for the event subscriber"""


class EventSubTranslator(EventSubscriberProtocol):
    """A translator that can consume events"""

    def __init__(
        self, *, config: EventSubTranslatorConfig, orchestrator: OrchestratorPort
    ):
        self.topics_of_interest = [config.iva_state_changed_topic, config.auth_topic]
        self.types_of_interest = [
            config.iva_state_changed_type,
            config.second_factor_recreated_type,
        ]
        self._config = config
        self._orchestrator = orchestrator

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
            case self._config.iva_state_changed_type:
                if key.startswith("all-"):
                    await self._handle_all_ivas_reset(payload=payload)
                else:
                    await self._handle_iva_state_change(payload=payload)
            case self._config.second_factor_recreated_type:
                await self._handle_second_factor_recreated(payload=payload)


class OutboxSubTranslatorConfig(UserEventsConfig, AccessRequestEventsConfig):
    """Config for the outbox subscriber"""


class UserOutboxTranslator(DaoSubscriberProtocol[event_schemas.User]):
    """A class that consumes User events conveying changes in DB resources."""

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
        self.event_topic = config.user_topic

    async def changed(self, resource_id: str, update: event_schemas.User) -> None:
        """Consume change event (created or updated) for user data."""
        await self._orchestrator.upsert_user_data(
            resource_id=resource_id, update=update
        )

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the deletion of a user."""
        await self._orchestrator.delete_user_data(resource_id=resource_id)


class AccessRequestOutboxTranslator(
    DaoSubscriberProtocol[event_schemas.AccessRequestDetails]
):
    """A class that consumes User events conveying changes in DB resources."""

    event_topic: str
    dto_model = event_schemas.AccessRequestDetails

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        orchestrator: OrchestratorPort,
    ):
        self._config = config
        self._orchestrator = orchestrator
        self.event_topic = config.access_request_topic

    async def changed(
        self, resource_id: str, update: event_schemas.AccessRequestDetails
    ) -> None:
        """Consume change event (created or updated) for access_request data."""
        await self._orchestrator.upsert_access_request(access_request=update)

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the deletion of a user."""
        await self._orchestrator.delete_access_request(resource_id=resource_id)
