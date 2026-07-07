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

"""Outbound DAO adapter - wires DTO models to MongoDB/Kafka via the outbox pattern."""

from ghga_event_schemas.configs import (
    FileAccessionMappingEventsConfig,
    ResearchDataUploadBoxEventsConfig,
)
from ghga_event_schemas.pydantic_ import FileAccessionMapping
from hexkit.providers.mongodb import MongoDbIndex
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory
from pydantic import Field
from pydantic_settings import BaseSettings

from rs.constants import (
    FILE_ACCESSION_COLLECTION,
    RESEARCH_DATA_UPLOAD_BOX_COLLECTION,
    STUDY_COLLECTION,
)
from rs.core.models import FileAccession, ResearchDataUploadBox, Study
from rs.ports.outbound.dao import BoxDao, FileAccessionDao, StudyDao

__all__ = [
    "OutboxPubConfig",
    "get_box_dao",
    "get_file_accession_dao",
    "get_study_dao",
]


# NOTE: Defined here temporarily. Should be moved to ghga_event_schemas once the
# Study schema is finalized, alongside the configs imported above.
class StudyEventsConfig(BaseSettings):
    """Config for events communicating changes in Studies.

    The event types are hardcoded by `hexkit`.
    """

    study_topic: str = Field(
        default=...,
        description="Name of the event topic containing study events",
        examples=["studies"],
    )


class OutboxPubConfig(
    ResearchDataUploadBoxEventsConfig,
    FileAccessionMappingEventsConfig,
    StudyEventsConfig,
):
    """Config needed to publish outbox events"""


def _file_accession_to_event(dto: FileAccession):
    """Translate a FileAccession into a FileAccessionMapping outbox event.

    Only mapped accessions (those with a file ID) are published; unmapped
    accessions return None, which suppresses the outbox event.
    """
    if dto.file_id is None:
        return None
    return FileAccessionMapping(accession=dto.pid, file_id=dto.file_id).model_dump(
        mode="json"
    )


async def get_file_accession_dao(
    *,
    config,
    dao_publisher_factory: MongoKafkaDaoPublisherFactory,
) -> FileAccessionDao:
    """Construct a FileAccession DAO from the shared factory."""
    return await dao_publisher_factory.get_dao(
        name=FILE_ACCESSION_COLLECTION,
        dto_model=FileAccession,
        id_field="pid",
        dto_to_event=_file_accession_to_event,
        event_topic=config.accession_map_topic,
        autopublish=True,
        indexes=[
            MongoDbIndex(fields="study_id"),
            MongoDbIndex(fields="file_id"),
        ],
    )


async def get_box_dao(
    *, config: OutboxPubConfig, dao_publisher_factory: MongoKafkaDaoPublisherFactory
) -> BoxDao:
    """Construct a ResearchDataUploadBox outbox DAO from the provided
    dao_publisher_factory.
    """
    if not dao_publisher_factory:
        raise RuntimeError("No DAO Factory and no override provided for BoxDao")

    return await dao_publisher_factory.get_dao(
        name=RESEARCH_DATA_UPLOAD_BOX_COLLECTION,
        dto_model=ResearchDataUploadBox,
        id_field="id",
        autopublish=True,
        dto_to_event=lambda dto: dto.model_dump(mode="json"),
        event_topic=config.research_data_upload_box_topic,
        indexes=[
            MongoDbIndex(fields="file_upload_box_id"),
            MongoDbIndex(fields="title", properties={"unique": True}),
        ],
    )


async def get_study_dao(
    *, config: OutboxPubConfig, dao_publisher_factory: MongoKafkaDaoPublisherFactory
) -> StudyDao:
    """Construct a Study outbox DAO from the provided dao_publisher_factory"""
    return await dao_publisher_factory.get_dao(
        name=STUDY_COLLECTION,
        dto_model=Study,
        id_field="id",
        autopublish=True,
        dto_to_event=lambda dto: dto.model_dump(mode="json"),
        event_topic=config.study_topic,
        indexes=[
            MongoDbIndex(fields="status"),
            MongoDbIndex(fields="title"),
        ],
    )
