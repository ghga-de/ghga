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
"""Adapter for publishing events to other services."""

import json

from ghga_event_schemas.pydantic_ import FileUploadValidationSuccess
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from fis.core.models import UploadMetadataBase
from fis.ports.outbound.event_pub import EventPublisherPort


class EventPubTranslatorConfig(BaseSettings):
    """Config for publishing events to other file backend services."""

    publisher_topic: str = Field(
        ...,
        description=(
            "Topic name expected by downstream services. Use the topic name from the "
            + "interrogation room service."
        ),
        examples=["file_interrogation"],
    )
    publisher_type: str = Field(
        ...,
        description=(
            "Type expected by downstream services. Use the type from the interrogation "
            + "room service."
        ),
        examples=["file_validation_success"],
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

    async def send_file_metadata(
        self,
        *,
        upload_metadata: UploadMetadataBase,
        source_bucket_id: str,
        secret_id: str,
        s3_endpoint_alias: str,
    ):
        """Send FileUploadValidationSuccess event to downstream services"""
        payload = FileUploadValidationSuccess(
            upload_date=now_as_utc().isoformat(),
            file_id=upload_metadata.file_id,
            object_id=upload_metadata.object_id,
            bucket_id=source_bucket_id,
            s3_endpoint_alias=s3_endpoint_alias,
            decrypted_size=upload_metadata.unencrypted_size,
            decryption_secret_id=secret_id,
            content_offset=0,
            encrypted_part_size=upload_metadata.part_size,
            encrypted_parts_md5=upload_metadata.encrypted_md5_checksums,
            encrypted_parts_sha256=upload_metadata.encrypted_sha256_checksums,
            decrypted_sha256=upload_metadata.unencrypted_checksum,
        )

        payload_dict = json.loads(payload.model_dump_json())

        await self._provider.publish(
            payload=payload_dict,
            type_=self._config.publisher_type,
            topic=self._config.publisher_topic,
            key=upload_metadata.file_id,
        )
