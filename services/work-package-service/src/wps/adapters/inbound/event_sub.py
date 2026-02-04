# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""KafkaEventSubscriber receiving events that announce datasets"""

import logging
from contextlib import suppress
from uuid import UUID

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import DatasetEventsConfig
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from wps.constants import TRACER
from wps.core.models import (
    Dataset,
    DatasetFile,
    ResearchDataUploadBoxBasics,
    WorkPackageType,
)
from wps.ports.inbound.repository import WorkPackageRepositoryPort

__all__ = [
    "EventSubTranslator",
    "EventSubTranslatorConfig",
    "OutboxSubTranslator",
    "OutboxSubTranslatorConfig",
]

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(DatasetEventsConfig):
    """Config for dataset creation related events."""


class OutboxSubTranslatorConfig(BaseSettings):
    """Config for listening to events carrying state updates for UploadBox objects

    The event types are hardcoded by `hexkit`.
    """

    # TODO: Replace this with standardized config from ghga-event-schemas when available
    upload_box_topic: str = Field(
        ...,
        description="Name of the event topic containing upload box events",
        examples=["upload-boxes"],
    )


class EventSubTranslator(EventSubscriberProtocol):
    """A triple hexagonal translator compatible with the EventSubscriberProtocol that
    is used to received events relevant for datasets.
    """

    def __init__(
        self,
        config: EventSubTranslatorConfig,
        work_package_repository: WorkPackageRepositoryPort,
    ):
        """Initialize with config parameters and core dependencies."""
        self.topics_of_interest = [
            config.dataset_change_topic,
        ]
        self.types_of_interest = [
            config.dataset_upsertion_type,
            config.dataset_deletion_type,
        ]
        self._dataset_upsertion_type = config.dataset_upsertion_type
        self._dataset_deletion_type = config.dataset_deletion_type
        self._repository = work_package_repository

    @TRACER.start_as_current_span("EventSubTranslator._handle_upsertion")
    async def _handle_upsertion(self, payload: JsonObject):
        """Handle event for new or changed datasets."""
        validated_payload = get_validated_payload(
            payload=payload,
            schema=event_schemas.MetadataDatasetOverview,
        )
        try:
            stage = WorkPackageType[validated_payload.stage.name]
        except KeyError:
            # stage does not correspond to a work type, ignore event
            log.info(
                "Ignoring dataset event with unknown stage %s",
                validated_payload.stage.name,
            )
            return

        files = [
            DatasetFile(
                id=payload_file.accession,
                extension=payload_file.file_extension,
                # we don't need the file description here for now
            )
            for payload_file in validated_payload.files
        ]
        dataset = Dataset(
            id=validated_payload.accession,
            title=validated_payload.title,
            stage=stage,
            description=validated_payload.description,
            files=files,
        )

        await self._repository.register_dataset(dataset)

    @TRACER.start_as_current_span("EventSubTranslator._handle_deletion")
    async def _handle_deletion(self, payload: JsonObject):
        """Handle event for deleted datasets."""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.MetadataDatasetID
        )
        with suppress(self._repository.DatasetNotFoundError):  # if already deleted
            await self._repository.delete_dataset(validated_payload.accession)

    async def _consume_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        topic: Ascii,
        key: Ascii,
        event_id: UUID,
    ) -> None:
        """
        Receive and process an event with already validated topic and type.

        Args:
            payload (JsonObject): The data/payload to send with the event.
            type_ (str): The type of the event.
            topic (str): Name of the topic the event was published to.
            key: A key used for routing the event.
        """
        if type_ == self._dataset_upsertion_type:
            await self._handle_upsertion(payload)
        elif type_ == self._dataset_deletion_type:
            await self._handle_deletion(payload)


class OutboxSubTranslator(DaoSubscriberProtocol):
    """Outbox-style event subscriber for UploadBox events"""

    event_topic: str
    dto_model = event_schemas.ResearchDataUploadBox

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        work_package_repository: WorkPackageRepositoryPort,
    ):
        self.event_topic = config.upload_box_topic
        self._repository = work_package_repository

    async def changed(
        self, resource_id: str, update: event_schemas.ResearchDataUploadBox
    ) -> None:
        """Consume a change event (created or updated) for the research data upload box
        with the given ID.
        """
        upload_box = ResearchDataUploadBoxBasics(
            id=update.id,
            file_upload_box_id=update.file_upload_box_id,
            title=update.title,
            description=update.description,
        )
        await self._repository.register_upload_box(upload_box=upload_box)

    async def deleted(self, resource_id: str) -> None:
        """Consume an event indicating the deletion of the research data upload box
        with the given ID.
        """
        with suppress(self._repository.UploadBoxNotFoundError):  # if already deleted
            await self._repository.delete_upload_box(UUID(resource_id))
