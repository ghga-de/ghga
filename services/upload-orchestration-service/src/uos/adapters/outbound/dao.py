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
"""DAO implementation"""

from ghga_event_schemas.configs import ResearchDataUploadBoxEventsConfig
from hexkit.protocols.daopub import DaoPublisherFactoryProtocol
from hexkit.providers.mongodb import MongoDbIndex
from pydantic import Field

from uos.constants import ACCESSION_MAPS_COLLECTION, BOX_COLLECTION
from uos.core.models import AccessionMap, ResearchDataUploadBox
from uos.ports.outbound.dao import AccessionMapDao, BoxDao

__all__ = ["OutboxPubConfig", "get_accession_map_dao", "get_box_dao"]


class OutboxPubConfig(ResearchDataUploadBoxEventsConfig):
    """Config needed to publish outbox events"""

    accession_map_topic: str = Field(
        default=...,
        description="The name of the topic used for file accession map outbox events",
        examples=["accession-maps", "file-accession-maps"],
    )


async def get_box_dao(
    *, config: OutboxPubConfig, dao_publisher_factory: DaoPublisherFactoryProtocol
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


async def get_accession_map_dao(
    *, config: OutboxPubConfig, dao_publisher_factory: DaoPublisherFactoryProtocol
) -> AccessionMapDao:
    """Construct an AccessionMap outbox DAO from the provided dao_publisher_factory."""
    return await dao_publisher_factory.get_dao(
        name=ACCESSION_MAPS_COLLECTION,
        dto_model=AccessionMap,
        id_field="box_id",
        dto_to_event=lambda dto: dto.mapping,
        event_topic=config.accession_map_topic,
        autopublish=True,
    )
