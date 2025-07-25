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

import logging
from contextlib import suppress
from uuid import UUID

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
from pydantic import UUID4

from nos.models import EventId
from nos.ports.inbound.orchestrator import OrchestratorPort
from nos.ports.outbound.dao import EventIdDaoPort, ResourceNotFoundError


class EventSubTranslatorConfig(
    IvaChangeEventsConfig, SecondFactorRecreatedEventsConfig
):
    """Config for the event subscriber"""


log = logging.getLogger(__name__)


class EventSubTranslator(EventSubscriberProtocol):
    """A translator that can consume events"""

    def __init__(
        self,
        *,
        config: EventSubTranslatorConfig,
        orchestrator: OrchestratorPort,
        event_id_dao: EventIdDaoPort,
    ):
        self.topics_of_interest = [config.iva_state_changed_topic, config.auth_topic]
        self.types_of_interest = [
            config.iva_state_changed_type,
            config.second_factor_recreated_type,
        ]
        self._config = config
        self._orchestrator = orchestrator
        self._event_id_dao = event_id_dao

    async def _have_we_seen_this_event(self, *, event_id: UUID4) -> bool:
        """Check if we have already processed this event."""
        with suppress(ResourceNotFoundError):
            await self._event_id_dao.get_by_id(event_id)
            return True
        return False

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
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
        event_id: UUID4,
    ) -> None:
        """Consumes an event"""
        if await self._have_we_seen_this_event(event_id=event_id):
            log.debug(
                "Event ID %s has already been processed, skipping further handling.",
                event_id,
            )
            return
        try:
            # Process the event based on its type
            match type_:
                case self._config.iva_state_changed_type:
                    if key.startswith("all-"):
                        await self._handle_all_ivas_reset(payload=payload)
                    else:
                        await self._handle_iva_state_change(payload=payload)
                case self._config.second_factor_recreated_type:
                    await self._handle_second_factor_recreated(payload=payload)

            # If processing is successful, insert the event ID into the database
            await self._event_id_dao.insert(EventId(event_id=event_id))
            log.debug("Inserted event ID %s into the database.", event_id)
        except Exception:
            # If an error occurs, we do not store the event ID, log and re-raise
            log.info("Didn't store event ID %s due to error in processing.", event_id)
            raise


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
        await self._orchestrator.upsert_user_data(update=update)

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the deletion of a user."""
        user_id = UUID(resource_id)  # this ID is canonically a UUID4
        await self._orchestrator.delete_user_data(user_id=user_id)


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
        access_request_id = UUID(resource_id)  # this ID is canonically a UUID4
        await self._orchestrator.delete_access_request(
            access_request_id=access_request_id
        )
