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
    FileInterrogationFailureEventsConfig,
    FileInterrogationSuccessEventsConfig,
)
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import UUID4

from fis.ports.outbound.event_pub import EventPubTranslatorPort


class EventPubConfig(
    FileInterrogationFailureEventsConfig,
    FileInterrogationSuccessEventsConfig,
):
    """Topic & type information for event publishing"""


class EventPubTranslator(EventPubTranslatorPort):
    """Translation between core and EventPublisherProtocol"""

    def __init__(
        self,
        *,
        config: EventPubConfig,
        provider: EventPublisherProtocol,
    ) -> None:
        """Configure with provider for the DaoFactoryProtocol"""
        self._provider = provider
        self._config = config

    async def publish_interrogation_success(  # noqa: PLR0913
        self,
        *,
        file_id: UUID4,
        secret_id: str,
        storage_alias: str,
        bucket_id: str,
        object_id: UUID4,
        interrogated_at: UTCDatetime,
        encrypted_parts_md5: list[str],
        encrypted_parts_sha256: list[str],
        encrypted_size: int,
    ):
        """Publish a file interrogation success event"""
        payload = event_schemas.InterrogationSuccess(
            file_id=file_id,
            secret_id=secret_id,
            storage_alias=storage_alias,
            bucket_id=bucket_id,
            object_id=object_id,
            interrogated_at=interrogated_at,
            encrypted_parts_md5=encrypted_parts_md5,
            encrypted_parts_sha256=encrypted_parts_sha256,
            encrypted_size=encrypted_size,
        )
        await self._provider.publish(
            payload=payload.model_dump(mode="json"),
            type_=self._config.interrogation_success_type,
            topic=self._config.file_interrogations_topic,
            key=str(file_id),
        )

    async def publish_interrogation_failed(
        self,
        *,
        file_id: UUID4,
        storage_alias: str,
        interrogated_at: UTCDatetime,
        reason: str,
    ):
        """Publish a file interrogation failure event"""
        payload = event_schemas.InterrogationFailure(
            file_id=file_id,
            storage_alias=storage_alias,
            interrogated_at=interrogated_at,
            reason=reason,
        )
        await self._provider.publish(
            payload=payload.model_dump(mode="json"),
            type_=self._config.interrogation_failure_type,
            topic=self._config.file_interrogations_topic,
            key=str(file_id),
        )
