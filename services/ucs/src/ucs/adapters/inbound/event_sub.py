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
"""Event subscriber configuration and class"""

from uuid import UUID

from ghga_event_schemas.configs import (
    FileDeletionRequestEventsConfig,
    FileInternallyRegisteredEventsConfig,
    FileInterrogationFailureEventsConfig,
    FileInterrogationSuccessEventsConfig,
)
from ghga_event_schemas.pydantic_ import (
    FileDeletionRequested,
    FileInternallyRegistered,
    InterrogationFailure,
    InterrogationSuccess,
)
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol

from ucs.constants import TRACER
from ucs.ports.inbound.controller import UploadControllerPort


class EventSubConfig(
    FileInterrogationFailureEventsConfig,
    FileInterrogationSuccessEventsConfig,
    FileInternallyRegisteredEventsConfig,
    FileDeletionRequestEventsConfig,
):
    """Event sub translator configuration"""


class EventSubTranslator(EventSubscriberProtocol):
    """An event subscriber translator class"""

    topics_of_interest: list[str]
    types_of_interest: list[str]

    def __init__(
        self, *, config: EventSubConfig, upload_controller: UploadControllerPort
    ):
        """Configure the translator"""
        self._config = config
        self.topics_of_interest = [
            config.file_interrogations_topic,
            config.file_internally_registered_topic,
            config.file_deletion_request_topic,
        ]
        self.types_of_interest = [
            config.interrogation_success_type,
            config.interrogation_failure_type,
            config.file_internally_registered_type,
            config.file_deletion_request_type,
        ]
        self._upload_controller = upload_controller

    @TRACER.start_as_current_span("EventSubTranslator._consume_interrogation_success")
    async def _consume_interrogation_success(self, *, payload: JsonObject):
        """Consume an InterrogationSuccess event"""
        validated_payload = get_validated_payload(payload, InterrogationSuccess)
        await self._upload_controller.process_interrogation_success(
            report=validated_payload
        )

    @TRACER.start_as_current_span("EventSubTranslator._consume_interrogation_failure")
    async def _consume_interrogation_failure(self, *, payload: JsonObject):
        """Consume an InterrogationFailure event"""
        validated_payload = get_validated_payload(payload, InterrogationFailure)
        await self._upload_controller.process_interrogation_failure(
            report=validated_payload
        )

    @TRACER.start_as_current_span(
        "EventSubTranslator._consume_file_internally_registered"
    )
    async def _consume_file_internally_registered(self, *, payload: JsonObject):
        """Consume a FileInternallyRegistered event"""
        validated_payload = get_validated_payload(payload, FileInternallyRegistered)
        await self._upload_controller.process_internal_file_registration(
            registration_metadata=validated_payload
        )

    @TRACER.start_as_current_span("EventSubTranslator._consume_file_deletion_requested")
    async def _consume_file_deletion_requested(self, *, payload: JsonObject):
        """Consume a FileDeletionRequested event"""
        validated_payload = get_validated_payload(payload, FileDeletionRequested)
        await self._upload_controller.process_file_deletion_requested(
            file_id=validated_payload.file_id
        )

    async def _consume_validated(
        self, *, payload: JsonObject, type_: str, topic: str, key: str, event_id: UUID
    ) -> None:
        if type_ == self._config.interrogation_success_type:
            await self._consume_interrogation_success(payload=payload)
        elif type_ == self._config.interrogation_failure_type:
            await self._consume_interrogation_failure(payload=payload)
        elif type_ == self._config.file_internally_registered_type:
            await self._consume_file_internally_registered(payload=payload)
        elif type_ == self._config.file_deletion_request_type:
            await self._consume_file_deletion_requested(payload=payload)
