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
from ghga_event_schemas.configs import (
    FileDeletionRequestEventsConfig,
    FileInternallyRegisteredEventsConfig,
    FileInterrogationFailureEventsConfig,
    FileMetadataEventsConfig,
)
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.protocols.eventsub import EventSubscriberProtocol

from ucs.core import models
from ucs.ports.inbound.file_service import FileMetadataServicePort
from ucs.ports.inbound.upload_service import UploadServicePort

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(
    FileMetadataEventsConfig,
    FileInterrogationFailureEventsConfig,
    FileInternallyRegisteredEventsConfig,
):
    """Config for receiving metadata on files to expect for upload."""


class EventSubTranslator(EventSubscriberProtocol):
    """A triple hexagonal translator compatible with the EventSubscriberProtocol that
    is used to received events relevant for file uploads.
    """

    def __init__(
        self,
        config: EventSubTranslatorConfig,
        file_metadata_service: FileMetadataServicePort,
        upload_service: UploadServicePort,
    ):
        """Initialize with config parameters and core dependencies."""
        self.topics_of_interest = [
            config.file_metadata_topic,
            config.file_internally_registered_topic,
            config.file_interrogations_topic,
        ]
        self.types_of_interest = [
            config.file_metadata_type,
            config.file_internally_registered_type,
            config.interrogation_failure_type,
        ]

        self._file_metadata_service = file_metadata_service
        self._upload_service = upload_service
        self._config = config

    async def _consume_file_metadata(self, *, payload: JsonObject) -> None:
        """Consume file registration events."""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.MetadataSubmissionUpserted
        )

        file_upserts = [
            models.FileMetadataUpsert(
                file_id=file.file_id,
                file_name=file.file_name,
                decrypted_sha256=file.decrypted_sha256,
                decrypted_size=file.decrypted_size,
            )
            for file in validated_payload.associated_files
        ]

        await self._file_metadata_service.upsert_multiple(files=file_upserts)

    async def _consume_upload_accepted(self, *, payload: JsonObject) -> None:
        """Consume upload accepted events."""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.FileInternallyRegistered
        )

        await self._upload_service.accept_latest(file_id=validated_payload.file_id)

    async def _consume_validation_failure(self, *, payload: JsonObject) -> None:
        """Consume file validation failure events."""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.FileUploadValidationFailure
        )

        await self._upload_service.reject_latest(file_id=validated_payload.file_id)

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
    ) -> None:
        """Consume events from the topics of interest."""
        if type_ == self._config.file_metadata_type:
            await self._consume_file_metadata(payload=payload)
        elif type_ == self._config.file_internally_registered_type:
            await self._consume_upload_accepted(payload=payload)
        elif type_ == self._config.interrogation_failure_type:
            await self._consume_validation_failure(payload=payload)
        else:
            raise RuntimeError(f"Unexpected event of type: {type_}")


class OutboxSubTranslatorConfig(FileDeletionRequestEventsConfig):
    """Config for the outbox subscriber"""


class FileDeletionRequestedListener(
    DaoSubscriberProtocol[event_schemas.FileDeletionRequested]
):
    """A class that consumes FileDeletionRequested events."""

    event_topic: str
    dto_model = event_schemas.FileDeletionRequested

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        upload_service: UploadServicePort,
    ):
        self._upload_service = upload_service
        self.event_topic = config.file_deletion_request_topic

    async def changed(
        self, resource_id: str, update: event_schemas.FileDeletionRequested
    ) -> None:
        """Consume change event for File Deletion Requests.
        Idempotence is handled by the core, so no intermediary is required.
        """
        await self._upload_service.deletion_requested(file_id=update.file_id)

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the deletion of a File Deletion Request."""
        log.warning(
            "Received DELETED-type event for FileDeletionRequested with resource ID '%s'",
            resource_id,
        )
