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

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import (
    DownloadServedEventsConfig,
    FileDeletedEventsConfig,
    FileRegisteredForDownloadEventsConfig,
)
from hexkit.protocols.eventpub import EventPublisherProtocol

from dcs.core import models
from dcs.ports.outbound.event_pub import EventPublisherPort


class EventPubTranslatorConfig(
    DownloadServedEventsConfig,
    FileDeletedEventsConfig,
    FileRegisteredForDownloadEventsConfig,
):
    """Config for publishing file download related events."""


class EventPubTranslator(EventPublisherPort):
    """A translator according to  the triple hexagonal architecture implementing
    the EventPublisherPort.
    """

    def __init__(
        self, *, config: EventPubTranslatorConfig, provider: EventPublisherProtocol
    ):
        """Initialize with configs and a provider of the EventPublisherProtocol."""
        self._config = config
        self._provider = provider

    async def download_served(
        self,
        *,
        drs_object: models.DrsObjectWithUri,
        target_bucket_id: str,
    ) -> None:
        """Communicate the event of a download being served. This can be relevant for
        auditing purposes.
        """
        payload = event_schemas.FileDownloadServed(
            s3_endpoint_alias=drs_object.s3_endpoint_alias,
            file_id=drs_object.file_id,
            target_object_id=drs_object.object_id,
            target_bucket_id=target_bucket_id,
            decrypted_sha256=drs_object.decrypted_sha256,
            context="unknown",
        )
        payload_dict = json.loads(payload.model_dump_json())

        await self._provider.publish(
            payload=payload_dict,
            type_=self._config.download_served_type,
            topic=self._config.download_served_topic,
            key=drs_object.file_id,
        )

    async def file_registered(self, *, drs_object: models.DrsObjectWithUri) -> None:
        """Communicates the event that a file has been registered."""
        payload = event_schemas.FileRegisteredForDownload(
            file_id=drs_object.file_id,
            decrypted_sha256=drs_object.decrypted_sha256,
            upload_date=drs_object.creation_date,
            drs_uri=drs_object.self_uri,
        )
        payload_dict = json.loads(payload.model_dump_json())

        await self._provider.publish(
            payload=payload_dict,
            type_=self._config.file_registered_for_download_type,
            topic=self._config.file_registered_for_download_topic,
            key=drs_object.file_id,
        )

    async def file_deleted(self, *, file_id: str) -> None:
        """Communicates the event that a file has been successfully deleted."""
        payload = event_schemas.FileDeletionSuccess(file_id=file_id)
        payload_dict = json.loads(payload.model_dump_json())

        await self._provider.publish(
            payload=payload_dict,
            type_=self._config.file_deleted_type,
            topic=self._config.file_deleted_topic,
            key=file_id,
        )
