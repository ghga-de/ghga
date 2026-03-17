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

from ghga_event_schemas.configs import (
    FileDeletionRequestEventsConfig,
    FileInterrogationSuccessEventsConfig,
    FileStagingRequestedEventsConfig,
    FileUploadEventsConfig,
)
from ghga_event_schemas.pydantic_ import FileDeletionRequested, NonStagedFileRequested
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import JsonObject
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import UUID4

from ifrs.constants import TRACER
from ifrs.core.models import FileUpload
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

    @TRACER.start_as_current_span("EventSubTranslator._consume_file_staging_request")
    async def _consume_file_staging_request(self, *, payload: JsonObject):
        """Consume an event requesting a file to be staged to the download bucket"""
        validated_payload = get_validated_payload(payload, NonStagedFileRequested)

        await self._file_registry.stage_registered_file(
            file_id=validated_payload.file_id,
            decrypted_sha256=validated_payload.decrypted_sha256,
            download_object_id=validated_payload.target_object_id,
            download_bucket_id=validated_payload.target_bucket_id,
        )

    @TRACER.start_as_current_span("EventSubTranslator._consume_file_deletion_request")
    async def _consume_file_deletion_request(self, *, payload: JsonObject):
        """Consume an event requesting a file to be deleted"""
        validated_payload = get_validated_payload(payload, FileDeletionRequested)
        await self._file_registry.delete_file(file_id=validated_payload.file_id)

    async def _consume_validated(
        self, *, payload: JsonObject, type_: str, topic: str, key: str, event_id: UUID4
    ):
        """Process an inbound event"""
        cfg = self._config
        match (topic, type_):
            case (cfg.files_to_stage_topic, cfg.files_to_stage_type):
                await self._consume_file_staging_request(payload=payload)
            case (cfg.file_deletion_request_topic, cfg.file_deletion_request_type):
                await self._consume_file_deletion_request(payload=payload)
            case _:
                raise RuntimeError(f"Unexpected event of type: {type_}")


class OutboxSubConfig(FileUploadEventsConfig):
    """Configuration for the outbox sub translator"""


class FileUploadOutboxTranslator(DaoSubscriberProtocol[FileUpload]):
    """An outbox subscriber event translator for FileUpload outbox events.

    FileUpload events will be received all throughout the FileUpload lifecycle,
    including initialization, upload, interrogation, and so on. IFRS is only interested
    in the events once they acquire the state of 'awaiting_archival'.
    """

    event_topic: str
    dto_model = FileUpload

    def __init__(self, *, config: OutboxSubConfig, file_registry: FileRegistryPort):
        """Initialize the outbox subscriber"""
        self.event_topic = config.file_upload_topic
        self._file_registry = file_registry

    @TRACER.start_as_current_span("FileUploadOutboxTranslator.changed")
    async def changed(self, resource_id: str, update: FileUpload) -> None:
        """Process a FileUpload event if the state is 'awaiting_archival'."""
        await self._file_registry.handle_file_upload(file_upload=update)

    @TRACER.start_as_current_span("FileUploadOutboxTranslator.deleted")
    async def deleted(self, resource_id: str) -> None:
        """This should not be hit.

        FileUploads are not deleted. Instead, their state is set to 'cancelled' or
        'failed'. If we receive a deletion event for a FileUpload, there is an
        inconsistency in implementation between services. The event should be sent
        to the DLQ.
        """
        log.error("Received deletion outbox event for FileUpload %s.", resource_id)
        raise RuntimeError(f"Unexpected deletion event for FileUpload {resource_id}.")
