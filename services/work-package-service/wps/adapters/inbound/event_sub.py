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
#

"""KafkaEventSubscriber receiving events that announce datasets"""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.validation import get_validated_payload
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import BaseSettings, Field

from wps.core.models import Dataset, DatasetFile, WorkType
from wps.ports.inbound.repository import WorkPackageRepositoryPort

__all__ = ["EventSubTranslatorConfig", "EventSubTranslator"]


class EventSubTranslatorConfig(BaseSettings):
    """Config for dataset creation related events."""

    dataset_overview_event_topic: str = Field(
        ...,
        description="Name of the topic for events that inform about datasets.",
        example="metadata",
    )
    dataset_overview_event_type: str = Field(
        ...,
        description="The type to use for events that inform about datasets.",
        example="metadata_dataset_overview",
    )


class EventSubTranslator(EventSubscriberProtocol):
    """A triple hexagonal translator compatible with the EventSubscriberProtocol that
    is used to received events relevant for file uploads."""

    def __init__(
        self,
        config: EventSubTranslatorConfig,
        work_package_repository: WorkPackageRepositoryPort,
    ):
        """Initialize with config parameters and core dependencies."""
        self.topics_of_interest = [
            config.dataset_overview_event_topic,
        ]
        self.types_of_interest = [
            config.dataset_overview_event_type,
        ]
        self._repository = work_package_repository

    async def _consume_validated(  # pylint: disable=unused-argument
        self, *, payload: JsonObject, type_: Ascii, topic: Ascii
    ) -> None:
        """
        Receive and process an event with already validated topic and type.

        Args:
            payload (JsonObject): The data/payload to send with the event.
            type_ (str): The type of the event.
            topic (str): Name of the topic the event was published to.
        """

        validated_payload = get_validated_payload(
            payload=payload,
            schema=event_schemas.MetadataDatasetOverview,
        )
        try:
            stage = WorkType[validated_payload.stage.name]
        except KeyError:
            # stage does not correspond to a work type, ignore event
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
