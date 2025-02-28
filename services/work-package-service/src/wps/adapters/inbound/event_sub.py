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
#

"""KafkaEventSubscriber receiving events that announce datasets"""

import logging
from contextlib import suppress

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import DatasetEventsConfig
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol

from wps.core.models import Dataset, DatasetFile, WorkType
from wps.ports.inbound.repository import WorkPackageRepositoryPort

__all__ = ["EventSubTranslator", "EventSubTranslatorConfig"]

log = logging.getLogger(__name__)


class EventSubTranslatorConfig(DatasetEventsConfig):
    """Config for dataset creation related events."""


class EventSubTranslator(EventSubscriberProtocol):
    """A triple hexagonal translator compatible with the EventSubscriberProtocol that
    is used to received events relevant for file uploads.
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

    async def _handle_upsertion(self, payload: JsonObject):
        """Handle event for new or changed datasets."""
        validated_payload = get_validated_payload(
            payload=payload,
            schema=event_schemas.MetadataDatasetOverview,
        )
        try:
            stage = WorkType[validated_payload.stage.name]
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

    async def _handle_deletion(self, payload: JsonObject):
        """Handle event for deleted datasets."""
        validated_payload = get_validated_payload(
            payload=payload, schema=event_schemas.MetadataDatasetID
        )
        with suppress(self._repository.DatasetNotFoundError):  # if already deleted
            await self._repository.delete_dataset(validated_payload.accession)

    async def _consume_validated(
        self, *, payload: JsonObject, type_: Ascii, topic: Ascii, key: Ascii
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
