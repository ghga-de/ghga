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
    async def file_internally_registered(self, *, file: models.FileMetadata) -> None:
        """Communicates the event that a new file has been internally registered."""
        payload = event_schemas.FileInternallyRegistered(
            file_id=file.id,
            archive_date=file.archive_date,
            storage_alias=file.storage_alias,
            bucket_id=file.bucket_id,
            secret_id=file.secret_id,
            decrypted_size=file.decrypted_size,
            encrypted_size=file.encrypted_size,
            decrypted_sha256=file.decrypted_sha256,
            encrypted_parts_md5=file.encrypted_parts_md5,
            encrypted_parts_sha256=file.encrypted_parts_sha256,
            part_size=file.part_size,
        )

        await self._provider.publish(
            payload=payload.model_dump(mode="json"),
            type_=self._config.file_internally_registered_type,
            topic=self._config.file_internally_registered_topic,
            key=str(file.id),
        )

    @TRACER.start_as_current_span("EventPubTranslator.file_deleted")
    async def file_deleted(self, *, file_id: UUID4) -> None:
        """Communicates the event that a file has been successfully deleted."""
        payload = event_schemas.FileDeletionSuccess(file_id=file_id)

        await self._provider.publish(
            payload=payload.model_dump(mode="json"),
            type_=self._config.file_deleted_type,
            topic=self._config.file_deleted_topic,
            key=str(file_id),
        )

    @TRACER.start_as_current_span("EventPubTranslator.file_staged_for_download")
    async def file_staged_for_download(
        self,
        *,
        file_id: UUID4,
        storage_alias: str,
        target_bucket_id: str,
        target_object_id: UUID4,
        decrypted_sha256: str,
    ) -> None:
        """Communicates the event that a file has been staged for download."""
        payload = event_schemas.FileStagedForDownload(
            file_id=file_id,
            storage_alias=storage_alias,
            target_bucket_id=target_bucket_id,
            target_object_id=target_object_id,
            decrypted_sha256=decrypted_sha256,
        )

        await self._provider.publish(
            payload=payload.model_dump(mode="json"),
            type_=self._config.file_staged_type,
            topic=self._config.file_staged_topic,
            key=str(file_id),
        )
