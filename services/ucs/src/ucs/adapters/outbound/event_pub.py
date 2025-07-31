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

"""Kafka-based event publishing adapters and the exception they may throw."""

from uuid import UUID

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import (
    FileDeletedEventsConfig,
    FileUploadReceivedEventsConfig,
)
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.protocols.eventpub import EventPublisherProtocol

from ucs.core import models
from ucs.ports.outbound.event_pub import EventPublisherPort


class EventPubTranslatorConfig(FileDeletedEventsConfig, FileUploadReceivedEventsConfig):
    """Config for publishing file upload- or deletion-related events."""


class EventPubTranslator(EventPublisherPort):
    """A translator (according to the triple hexagonal architecture) for publishing
    events using the EventPublisherProtocol.
    """

    def __init__(
        self, *, config: EventPubTranslatorConfig, provider: EventPublisherProtocol
    ):
        """Initialize with a suitable protocol provider."""
        self._config = config
        self._provider = provider

    async def publish_deletion_successful(self, *, file_id: str) -> None:
        """Publish event informing that deletion of data and metadata for the given file ID has succeeded."""
        event_payload = event_schemas.FileDeletionSuccess(file_id=file_id)

        await self._provider.publish(
            payload=event_payload.model_dump(),
            type_=self._config.file_deleted_type,
            topic=self._config.file_deleted_topic,
            key=file_id,
        )

    async def publish_upload_received(  # noqa: PLR0913
        self,
        *,
        file_metadata: models.FileMetadata,
        upload_date: UTCDatetime,
        submitter_public_key: str,
        object_id: str,
        bucket_id: str,
        storage_alias: str,
    ) -> None:
        """Publish an event relaying that a new file upload was received."""
        event_payload = event_schemas.FileUploadReceived(
            s3_endpoint_alias=storage_alias,
            file_id=file_metadata.file_id,
            object_id=UUID(object_id),
            bucket_id=bucket_id,
            upload_date=upload_date,
            submitter_public_key=submitter_public_key,
            decrypted_size=file_metadata.decrypted_size,
            expected_decrypted_sha256=file_metadata.decrypted_sha256,
        )
        await self._provider.publish(
            payload=event_payload.model_dump(),
            type_=self._config.file_upload_received_type,
            topic=self._config.file_upload_received_topic,
            key=event_payload.file_id,
        )
