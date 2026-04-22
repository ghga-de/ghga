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

"""Outbound DAO adapter — wires DTO models to MongoDB/Kafka via the outbox pattern."""

from ghga_event_schemas.configs import (
    FileAccessionMappingEventsConfig,
    ResearchDataUploadBoxEventsConfig,
)
from ghga_event_schemas.pydantic_ import FileAccessionMapping
from hexkit.providers.mongodb import MongoDbIndex
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from rs.constants import BOX_COLLECTION
from rs.core.models import ResearchDataUploadBox
from rs.ports.outbound.dao import BoxDao, FileAccessionMappingDao

__all__ = ["OutboxPubConfig", "get_box_dao", "get_file_accession_mapping_dao"]


class OutboxPubConfig(
    ResearchDataUploadBoxEventsConfig, FileAccessionMappingEventsConfig
):
    """Config needed to publish outbox events"""


async def get_file_accession_mapping_dao(
    *,
    config,
    dao_publisher_factory: MongoKafkaDaoPublisherFactory,
) -> FileAccessionMappingDao:
    """Construct a FileAccessionMapping DAO from the shared factory."""
    return await dao_publisher_factory.get_dao(
        name=config.file_accession_mappings_collection,
        dto_model=FileAccessionMapping,
        id_field="accession",
        dto_to_event=lambda event: event.model_dump(mode="json"),
        event_topic=config.accession_map_topic,
        autopublish=True,
    )


async def get_box_dao(
    *, config: OutboxPubConfig, dao_publisher_factory: MongoKafkaDaoPublisherFactory
) -> BoxDao:
    """Construct a ResearchDataUploadBox outbox DAO from the provided dao_publisher_factory"""
    if not dao_publisher_factory:
        raise RuntimeError("No DAO Factory and no override provided for BoxDao")

    return await dao_publisher_factory.get_dao(
        name=BOX_COLLECTION,
        dto_model=ResearchDataUploadBox,
        id_field="id",
        autopublish=True,
        dto_to_event=lambda dto: dto.model_dump(mode="json"),
        event_topic=config.research_data_upload_box_topic,
        indexes=[MongoDbIndex(fields="file_upload_box_id")],
    )
