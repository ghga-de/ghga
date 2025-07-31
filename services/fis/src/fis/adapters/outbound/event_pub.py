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

from ghga_event_schemas.configs import FileInterrogationSuccessEventsConfig
from ghga_event_schemas.pydantic_ import FileUploadValidationSuccess
from hexkit.protocols.eventpub import EventPublisherProtocol
from hexkit.utils import now_utc_ms_prec

from fis.core import models
from fis.ports.outbound.event_pub import EventPubTranslatorPort


class EventPubTranslatorConfig(FileInterrogationSuccessEventsConfig):
    """Configuration for publishing events"""


class EventPubTranslator(EventPubTranslatorPort):
    """Translation between core and EventPublisherProtocol"""

    def __init__(
        self,
        *,
        config: EventPubTranslatorConfig,
        provider: EventPublisherProtocol,
    ) -> None:
        """Configure with provider for the DaoFactoryProtocol"""
        self._provider = provider
        self._config = config

    async def publish_file_interrogation_success(
        self,
        *,
        upload_metadata: models.UploadMetadataBase,
        secret_id: str,
    ):
        """Send FileUploadValidationSuccess event to downstream services"""
        payload = FileUploadValidationSuccess(
            upload_date=now_utc_ms_prec(),
            file_id=upload_metadata.file_id,
            object_id=upload_metadata.object_id,
            bucket_id=upload_metadata.bucket_id,
            s3_endpoint_alias=upload_metadata.storage_alias,
            decrypted_size=upload_metadata.unencrypted_size,
            decryption_secret_id=secret_id,
            content_offset=0,
            encrypted_part_size=upload_metadata.part_size,
            encrypted_parts_md5=upload_metadata.encrypted_md5_checksums,
            encrypted_parts_sha256=upload_metadata.encrypted_sha256_checksums,
            decrypted_sha256=upload_metadata.unencrypted_checksum,
        )
        await self._provider.publish(
            payload=payload.model_dump(),
            type_=self._config.interrogation_success_type,
            key=payload.file_id,
            topic=self._config.file_interrogations_topic,
        )
