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

"""Adapter for publishing events to other services."""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import (
    FileDeletedEventsConfig,
    FileInternallyRegisteredEventsConfig,
    FileStagedEventsConfig,
)
from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import UUID4

from ifrs.constants import TRACER
from ifrs.core import models
from ifrs.ports.outbound.event_pub import EventPublisherPort


class EventPubTranslatorConfig(
    FileStagedEventsConfig,
    FileDeletedEventsConfig,
    FileInternallyRegisteredEventsConfig,
):
    """Config for publishing internal events to the outside."""


class EventPubTranslator(EventPublisherPort):
    """A translator according to the triple hexagonal architecture implementing
    the EventPublisherPort.
    """

    def __init__(
        self, *, config: EventPubTranslatorConfig, provider: EventPublisherProtocol
    ):
        """Initialize with configs and a provider of the EventPublisherProtocol."""
        self._config = config
        self._provider = provider

    @TRACER.start_as_current_span("EventPubTranslator.file_internally_registered")
    async def file_internally_registered(
        self, *, file: models.FileMetadata, bucket_id: str
    ) -> None:
        """Communicates the event that a new file has been internally registered."""
        payload = event_schemas.FileInternallyRegistered(
            s3_endpoint_alias=file.storage_alias,
            file_id=file.file_id,
            object_id=file.object_id,
            bucket_id=bucket_id,
            decrypted_sha256=file.decrypted_sha256,
            decrypted_size=file.decrypted_size,
            decryption_secret_id=file.decryption_secret_id,
            content_offset=file.content_offset,
            encrypted_size=file.object_size,
            encrypted_part_size=file.encrypted_part_size,
            encrypted_parts_md5=file.encrypted_parts_md5,
            encrypted_parts_sha256=file.encrypted_parts_sha256,
            upload_date=file.upload_date,
        )

        await self._provider.publish(
            payload=payload.model_dump(mode="json"),
            type_=self._config.file_internally_registered_type,
            topic=self._config.file_internally_registered_topic,
            key=file.file_id,
        )

    @TRACER.start_as_current_span("EventPubTranslator.file_staged_for_download")
    async def file_staged_for_download(
        self,
        *,
        file_id: str,
        decrypted_sha256: str,
        target_object_id: UUID4,
        target_bucket_id: str,
        storage_alias: str,
    ) -> None:
        """Communicates the event that a file has been staged for download."""
        payload = event_schemas.FileStagedForDownload(
            s3_endpoint_alias=storage_alias,
            file_id=file_id,
            decrypted_sha256=decrypted_sha256,
            target_object_id=target_object_id,
            target_bucket_id=target_bucket_id,
        )

        await self._provider.publish(
            payload=payload.model_dump(mode="json"),
            type_=self._config.file_staged_type,
            topic=self._config.file_staged_topic,
            key=file_id,
        )

    @TRACER.start_as_current_span("EventPubTranslator.file_deleted")
    async def file_deleted(self, *, file_id: str) -> None:
        """Communicates the event that a file has been successfully deleted."""
        payload = event_schemas.FileDeletionSuccess(file_id=file_id)

        await self._provider.publish(
            payload=payload.model_dump(),
            type_=self._config.file_deleted_type,
            topic=self._config.file_deleted_topic,
            key=file_id,
        )
