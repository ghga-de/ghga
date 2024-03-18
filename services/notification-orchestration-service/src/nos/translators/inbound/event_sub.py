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
"""Event subscriber definition."""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
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
    access_request_created_type: str = Field(
        default=...,
        description="The type to use for access request created events",
        examples=["access_request_created"],
    )
    access_request_allowed_type: str = Field(
        default=...,
        description="The type to use for access request allowed events",
        examples=["access_request_allowed"],
    )
    access_request_denied_type: str = Field(
        default=...,
        description="The type to use for access request denied events",
        examples=["access_request_denied"],
    )
    file_registered_event_topic: str = Field(
        default=...,
        description="The name of the topic containing internal file registration events.",
        examples=["internal_file_registry"],
    )
    file_registered_event_type: str = Field(
        default=...,
        description="The type used for events detailing internally file registrations.",
        examples=["file_registered"],
    )


class EventSubTranslator(EventSubscriberProtocol):
    """A translator that can consume events"""

    def __init__(
        self, *, config: EventSubTranslatorConfig, orchestrator: OrchestratorPort
    ):
        self.topics_of_interest = [
            config.access_request_events_topic,
            config.file_registered_event_topic,
        ]
        self.types_of_interest = [
            config.access_request_created_type,
            config.access_request_allowed_type,
            config.access_request_denied_type,
            config.file_registered_event_type,
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

    async def _handle_file_registered(self, payload: JsonObject) -> None:
        """Send notifications for internal file registrations (completed uploads)."""
        validated_payload = get_validated_payload(
            payload, event_schemas.FileInternallyRegistered
        )
        await self._orchestrator.process_file_registered_notification(
            file_id=validated_payload.file_id
        )

    async def _consume_validated(
        self, *, payload: JsonObject, type_: Ascii, topic: Ascii
    ) -> None:
        """Consumes an event"""
        if type_ in (
            self._config.access_request_created_type,
            self._config.access_request_allowed_type,
            self._config.access_request_denied_type,
        ):
            await self._handle_access_request(type_, payload)
        elif type_ == self._config.file_registered_event_type:
            await self._handle_file_registered(payload=payload)
