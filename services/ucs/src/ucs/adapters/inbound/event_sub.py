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

from ucs.core import models
from ucs.ports.inbound.file_service import FileMetadataServicePort
from ucs.ports.inbound.upload_service import UploadServicePort

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(BaseSettings):
    """Config for receiving metadata on files to expect for upload."""

    file_metadata_event_topic: str = Field(
        default=...,
        description=(
            "Name of the topic to receive new or changed metadata on files that shall"
            + " be registered for uploaded."
        ),
        examples=["metadata"],
    )
    file_metadata_event_type: str = Field(
        default=...,
        description=(
            "The type used for events to receive new or changed metadata on files that"
            + " are expected to be uploaded."
        ),
        examples=["file_metadata_upserts"],
    )
    upload_accepted_event_topic: str = Field(
        default=...,
        description=(
            "Name of the topic to receive event that indicate that an upload was"
            + " by downstream services."
        ),
        examples=["internal_file_registry"],
    )
    upload_accepted_event_type: str = Field(
        default=...,
        description=(
            "The type used for event that indicate that an upload was by downstream"
            + " services."
        ),
        examples=["file_registered"],
    )
    upload_rejected_event_topic: str = Field(
        default=...,
        description="Name of the topic used for events informing about rejection of an "
        + "upload by downstream services due to validation failure.",
        examples=["file_interrogation"],
    )
    upload_rejected_event_type: str = Field(
        default=...,
        description="The type used for events informing about the failure of a file validation.",
        examples=["file_validation_failure"],
    )


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
            config.file_metadata_event_topic,
            config.upload_accepted_event_topic,
            config.upload_rejected_event_topic,
        ]
        self.types_of_interest = [
            config.file_metadata_event_type,
            config.upload_accepted_event_type,
            config.upload_rejected_event_type,
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
        if type_ == self._config.file_metadata_event_type:
            await self._consume_file_metadata(payload=payload)
        elif type_ == self._config.upload_accepted_event_type:
            await self._consume_upload_accepted(payload=payload)
        elif type_ == self._config.upload_rejected_event_type:
            await self._consume_validation_failure(payload=payload)
        else:
            raise RuntimeError(f"Unexpected event of type: {type_}")


class OutboxSubTranslatorConfig(BaseSettings):
    """Config for the outbox subscriber"""

    files_to_delete_topic: str = Field(
        default=...,
        description="The name of the topic for events informing about files to be deleted.",
        examples=["file_deletions"],
    )


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
        self.event_topic = config.files_to_delete_topic

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
