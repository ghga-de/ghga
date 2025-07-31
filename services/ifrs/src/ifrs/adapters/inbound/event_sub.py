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

"""Adapter for receiving events providing metadata on files"""

import logging

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import (
    FileDeletionRequestEventsConfig,
    FileInterrogationSuccessEventsConfig,
    FileStagingRequestedEventsConfig,
)
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import JsonObject
from hexkit.opentelemetry import start_span
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import UUID4

from ifrs.core.models import FileMetadataBase
from ifrs.ports.inbound.file_registry import FileRegistryPort

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(
    FileStagingRequestedEventsConfig,
    FileDeletionRequestEventsConfig,
    FileInterrogationSuccessEventsConfig,
):
    """Config for the event subscriber"""


class EventSubTranslator(EventSubscriberProtocol):
    """An event sub translator"""

    def __init__(
        self, config: EventSubTranslatorConfig, file_registry: FileRegistryPort
    ):
        self._file_registry = file_registry
        self._config = config
        self.topics_of_interest = [
            config.files_to_stage_topic,
            config.file_deletion_request_topic,
            config.file_interrogations_topic,
        ]
        self.types_of_interest = [
            config.files_to_stage_type,
            config.file_deletion_request_type,
            config.interrogation_success_type,
        ]

    @start_span()
    async def _consume_file_staging_request(self, *, payload: JsonObject):
        """Consume an event requesting a file to be staged to the outbox bucket"""
        validated_payload = get_validated_payload(
            payload, event_schemas.NonStagedFileRequested
        )

        await self._file_registry.stage_registered_file(
            file_id=validated_payload.file_id,
            decrypted_sha256=validated_payload.decrypted_sha256,
            outbox_object_id=validated_payload.target_object_id,
            outbox_bucket_id=validated_payload.target_bucket_id,
        )

    @start_span()
    async def _consume_file_deletion_request(self, *, payload: JsonObject):
        """Consume an event requesting a file to be deleted"""
        validated_payload = get_validated_payload(
            payload, event_schemas.FileDeletionRequested
        )
        await self._file_registry.delete_file(file_id=validated_payload.file_id)

    @start_span()
    async def _consume_file_interrogation_success(self, *, payload: JsonObject):
        """Consume an event indicating that a file has passed validation"""
        validated_payload = get_validated_payload(
            payload, event_schemas.FileUploadValidationSuccess
        )
        file_without_object_id = FileMetadataBase(
            file_id=validated_payload.file_id,
            decrypted_sha256=validated_payload.decrypted_sha256,
            decrypted_size=validated_payload.decrypted_size,
            upload_date=validated_payload.upload_date,
            decryption_secret_id=validated_payload.decryption_secret_id,
            encrypted_part_size=validated_payload.encrypted_part_size,
            encrypted_parts_md5=validated_payload.encrypted_parts_md5,
            encrypted_parts_sha256=validated_payload.encrypted_parts_sha256,
            content_offset=validated_payload.content_offset,
            storage_alias=validated_payload.s3_endpoint_alias,
        )

        await self._file_registry.register_file(
            file_without_object_id=file_without_object_id,
            staging_object_id=validated_payload.object_id,
            staging_bucket_id=validated_payload.bucket_id,
        )

    async def _consume_validated(
        self, *, payload: JsonObject, type_: str, topic: str, key: str, event_id: UUID4
    ):
        """Process an inbound event"""
        if (
            topic == self._config.files_to_stage_topic
            and type_ == self._config.files_to_stage_type
        ):
            await self._consume_file_staging_request(payload=payload)
        elif (
            topic == self._config.file_deletion_request_topic
            and type_ == self._config.file_deletion_request_type
        ):
            await self._consume_file_deletion_request(payload=payload)
        elif (
            topic == self._config.file_interrogations_topic
            and type_ == self._config.interrogation_success_type
        ):
            await self._consume_file_interrogation_success(payload=payload)
        else:
            raise RuntimeError(f"Unexpected event of type: {type_}")
