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

"""Receive events informing about files that are expected to be uploaded."""

import logging

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import (
    DatasetEventsConfig,
    FileDeletionRequestEventsConfig,
    FileInternallyRegisteredEventsConfig,
)
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import UUID4

from dins.ports.inbound.information_service import InformationServicePort

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(
    DatasetEventsConfig,
    FileInternallyRegisteredEventsConfig,
    FileDeletionRequestEventsConfig,
):
    """Config for publishing file upload-related events."""


class EventSubTranslator(EventSubscriberProtocol):
    """A triple hexagonal translator compatible with the EventSubscriberProtocol that
    is used to received events relevant for file uploads.
    """

    def __init__(
        self,
        config: EventSubTranslatorConfig,
        information_service: InformationServicePort,
    ):
        """Initialize with config parameters and core dependencies."""
        self._config = config
        self._information_service = information_service

        self.topics_of_interest = [
            config.dataset_change_topic,
            config.file_internally_registered_topic,
            config.file_deletion_request_topic,
        ]
        self.types_of_interest = [
            config.dataset_deletion_type,
            config.dataset_upsertion_type,
            config.file_internally_registered_type,
            config.file_deletion_request_type,
        ]

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: str,
        event_id: UUID4,
    ) -> None:
        """
        Receive and process an event with already validated topic and type.

        Args:
            payload (JsonObject): The data/payload to send with the event.
            type_ (str): The type of the event.
            topic (str): Name of the topic the event was published to.
            key (str): The key associated with the event.
        """
        if type_ == self._config.file_internally_registered_type:
            await self._consume_file_internally_registered(payload=payload)
        elif type_ == self._config.dataset_upsertion_type:
            await self._consume_dataset_upserted(payload=payload)
        elif type_ == self._config.dataset_deletion_type:
            await self._consume_dataset_deleted(payload=payload)
        elif type_ == self._config.file_deletion_request_type:
            await self._consume_file_deletion_requested(payload=payload)
        else:
            raise RuntimeError(f"Unexpected event of type: {type_}")

    async def _consume_file_internally_registered(self, *, payload: JsonObject):
        """
        Consume confirmation event that object data has been moved to permanent storage
        and the associated relevant metadata should be presented by this service.
        """
        validated_payload = get_validated_payload(
            payload=payload,
            schema=event_schemas.FileInternallyRegistered,
        )

        await self._information_service.register_file_information(
            file=validated_payload
        )

    async def _consume_dataset_upserted(self, *, payload: JsonObject):
        """Consume newly registered dataset to store file ID mapping."""
        validated_payload = get_validated_payload(
            payload=payload,
            schema=event_schemas.MetadataDatasetOverview,
        )

        await self._information_service.register_dataset_information(
            dataset=validated_payload
        )

    async def _consume_dataset_deleted(self, *, payload: JsonObject):
        """Delete information for registered dataset mappings when a dataset is deleted."""
        validated_payload = get_validated_payload(
            payload=payload,
            schema=event_schemas.MetadataDatasetID,
        )

        await self._information_service.delete_dataset_information(
            dataset_id=validated_payload.accession
        )

    async def _consume_file_deletion_requested(self, *, payload: JsonObject):
        """Consume an event requesting that a file deletion."""
        validated_payload = get_validated_payload(
            payload=payload,
            schema=event_schemas.FileDeletionRequested,
        )
        await self._information_service.delete_file_information(
            file_id=validated_payload.file_id
        )
