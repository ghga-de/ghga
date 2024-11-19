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

"""Adapter for receiving events providing metadata on files"""

import logging

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.daosub import DaoSubscriberProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from ifrs.core.models import FileMetadataBase
from ifrs.ports.inbound.file_registry import FileRegistryPort

log = logging.getLogger(__name__)


class OutboxSubTranslatorConfig(BaseSettings):
    """Config for the outbox subscriber"""

    files_to_delete_topic: str = Field(
        default=...,
        description="The name of the topic to receive events informing about files to delete.",
        examples=["file-deletions"],
    )
    files_to_register_topic: str = Field(
        default=...,
        description="The name of the topic to receive events informing about new files "
        + "to register.",
        examples=["file-interrogations"],
    )
    files_to_stage_topic: str = Field(
        default=...,
        description="The name of the topic to receive events informing about files to stage.",
        examples=["file-downloads"],
    )


class NonstagedFileRequestedTranslator(
    DaoSubscriberProtocol[event_schemas.NonStagedFileRequested]
):
    """A class that consumes NonStagedFileRequested events."""

    event_topic: str
    dto_model = event_schemas.NonStagedFileRequested

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        file_registry: FileRegistryPort,
    ):
        self._file_registry = file_registry
        self.event_topic = config.files_to_stage_topic

    async def changed(
        self, resource_id: str, update: event_schemas.NonStagedFileRequested
    ) -> None:
        """Consume change event (created or updated) for download request data."""
        await self._file_registry.stage_registered_file(
            file_id=resource_id,
            decrypted_sha256=update.decrypted_sha256,
            outbox_object_id=update.target_object_id,
            outbox_bucket_id=update.target_bucket_id,
        )

    async def deleted(self, resource_id: str) -> None:
        """This should never be called because these events are stateless and not saved."""
        log.error(
            "Received DELETED-type event for NonStagedFileRequested with resource ID '%s'",
            resource_id,
        )


class FileDeletionRequestedTranslator(
    DaoSubscriberProtocol[event_schemas.FileDeletionRequested]
):
    """A class that consumes FileDeletionRequested events."""

    event_topic: str
    dto_model = event_schemas.FileDeletionRequested

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        file_registry: FileRegistryPort,
    ):
        self._file_registry = file_registry
        self.event_topic = config.files_to_delete_topic

    async def changed(
        self, resource_id: str, update: event_schemas.FileDeletionRequested
    ) -> None:
        """Consume change event (created or updated) for File Deletion Requests."""
        await self._file_registry.delete_file(file_id=resource_id)

    async def deleted(self, resource_id: str) -> None:
        """This should never be called because these events are stateless and not saved."""
        log.error(
            "Received DELETED-type event for FileDeletionRequested with resource ID '%s'",
            resource_id,
        )


class FileValidationSuccessTranslator(
    DaoSubscriberProtocol[event_schemas.FileUploadValidationSuccess]
):
    """A class that consumes FileUploadValidationSuccess events."""

    event_topic: str
    dto_model = event_schemas.FileUploadValidationSuccess

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        file_registry: FileRegistryPort,
    ):
        self._file_registry = file_registry
        self.event_topic = config.files_to_register_topic

    async def changed(
        self, resource_id: str, update: event_schemas.FileUploadValidationSuccess
    ) -> None:
        """Consume change event (created or updated) for FileUploadValidationSuccess events."""
        file_without_object_id = FileMetadataBase(
            file_id=resource_id,
            decrypted_sha256=update.decrypted_sha256,
            decrypted_size=update.decrypted_size,
            upload_date=update.upload_date,
            decryption_secret_id=update.decryption_secret_id,
            encrypted_part_size=update.encrypted_part_size,
            encrypted_parts_md5=update.encrypted_parts_md5,
            encrypted_parts_sha256=update.encrypted_parts_sha256,
            content_offset=update.content_offset,
            storage_alias=update.s3_endpoint_alias,
        )

        await self._file_registry.register_file(
            file_without_object_id=file_without_object_id,
            staging_object_id=update.object_id,
            staging_bucket_id=update.bucket_id,
        )

    async def deleted(self, resource_id: str) -> None:
        """This should never be called because these events are stateless and not saved."""
        log.error(
            "Received DELETED-type event for FileUploadValidationSuccess with resource ID '%s'",
            resource_id,
        )
