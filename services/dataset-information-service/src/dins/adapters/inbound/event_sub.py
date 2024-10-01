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

"""Receive events informing about files that are expected to be uploaded."""

import logging

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from dins.ports.inbound.information_service import InformationServicePort

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(BaseSettings):
    """Config for publishing file upload-related events."""

    file_registered_event_topic: str = Field(
        default=...,
        description="The name of the topic for events informing about new registered files"
        " for which the metadata should be made available.",
        examples=["internal-file-registry"],
    )
    file_registered_event_type: str = Field(
        default=...,
        description="The name of the type used for events informing about new registered files"
        " for which the metadata should be made available.",
        examples=["file_registered"],
    )


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

        self.topics_of_interest = [config.file_registered_event_topic]
        self.types_of_interest = [config.file_registered_event_type]

    async def _consume_validated(
        self, *, payload: JsonObject, type_: Ascii, topic: Ascii, key: str
    ) -> None:
        """
        Receive and process an event with already validated topic and type.

        Args:
            payload (JsonObject): The data/payload to send with the event.
            type_ (str): The type of the event.
            topic (str): Name of the topic the event was published to.
            key (str): The key associated with the event.
        """
        if type_ == self._config.file_registered_event_type:
            await self._consume_file_internally_registered(payload=payload)
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

        await self._information_service.register_information(
            file_registered=validated_payload
        )


class OutboxSubTranslatorConfig(BaseSettings):
    """Config for the outbox subscriber"""

    files_to_delete_topic: str = Field(
        default=...,
        description="The name of the topic for events informing about files to be deleted.",
        examples=["file-deletions"],
    )


class InformationDeletionRequestedListener(
    DaoSubscriberProtocol[event_schemas.FileDeletionRequested]
):
    """A class that consumes FileDeletionRequested events."""

    event_topic: str
    dto_model = event_schemas.FileDeletionRequested

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        information_service: InformationServicePort,
    ):
        self.event_topic = config.files_to_delete_topic
        self.information_service = information_service

    async def changed(
        self, resource_id: str, update: event_schemas.FileDeletionRequested
    ) -> None:
        """Consume change event for File Deletion Requests."""
        await self.information_service.deletion_requested(file_id=update.file_id)

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the deletion of a File Deletion Request."""
        log.warning(
            "Received DELETED-type event for FileDeletionRequested with resource ID '%s'",
            resource_id,
        )
