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

"""Adapter for publishing events to other services."""

import json

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from ifrs.core import models
from ifrs.ports.outbound.event_pub import EventPublisherPort


class EventPubTranslatorConfig(BaseSettings):
    """Config for publishing internal events to the outside."""

    file_registered_event_topic: str = Field(
        ...,
        description="Name of the topic used for events indicating that a new file has"
        + " been internally registered.",
        examples=["internal_file_registry"],
    )
    file_registered_event_type: str = Field(
        ...,
        description="The type used for events indicating that a new file has"
        + " been internally registered.",
        examples=["file_registered"],
    )
    file_staged_event_topic: str = Field(
        ...,
        description="Name of the topic used for events indicating that a new file has"
        + " been internally registered.",
        examples=["internal_file_registry"],
    )
    file_staged_event_type: str = Field(
        ...,
        description="The type used for events indicating that a new file has"
        + " been internally registered.",
        examples=["file_staged_for_download"],
    )
    file_deleted_event_topic: str = Field(
        ...,
        description="Name of the topic used for events indicating that a file has"
        + " been deleted.",
        examples=["internal_file_registry"],
    )
    file_deleted_event_type: str = Field(
        ...,
        description="The type used for events indicating that a file has"
        + " been deleted.",
        examples=["file_deleted"],
    )


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
            encrypted_part_size=file.encrypted_part_size,
            encrypted_parts_md5=file.encrypted_parts_md5,
            encrypted_parts_sha256=file.encrypted_parts_sha256,
            upload_date=file.upload_date,
        )
        payload_dict = json.loads(payload.model_dump_json())

        await self._provider.publish(
            payload=payload_dict,
            type_=self._config.file_registered_event_type,
            topic=self._config.file_registered_event_topic,
            key=file.file_id,
        )

    async def file_staged_for_download(  # noqa: PLR0913
        self,
        *,
        file_id: str,
        decrypted_sha256: str,
        target_object_id: str,
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
        payload_dict = json.loads(payload.model_dump_json())

        await self._provider.publish(
            payload=payload_dict,
            type_=self._config.file_staged_event_type,
            topic=self._config.file_staged_event_topic,
            key=file_id,
        )

    async def file_deleted(self, *, file_id: str) -> None:
        """Communicates the event that a file has been successfully deleted."""
        payload = event_schemas.FileDeletionSuccess(file_id=file_id)
        payload_dict = json.loads(payload.model_dump_json())

        await self._provider.publish(
            payload=payload_dict,
            type_=self._config.file_deleted_event_type,
            topic=self._config.file_deleted_event_topic,
            key=file_id,
        )
