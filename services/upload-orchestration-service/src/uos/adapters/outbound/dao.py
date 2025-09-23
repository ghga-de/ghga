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
"""DAO implementation"""

from ghga_event_schemas.configs import ResearchDataUploadBoxEventsConfig
from ghga_event_schemas.pydantic_ import ResearchDataUploadBox
from hexkit.protocols.daopub import DaoPublisherFactoryProtocol

from uos.constants import BOX_COLLECTION
from uos.ports.outbound.dao import BoxDao

__all__ = ["OutboxPubConfig", "get_box_dao"]


class OutboxPubConfig(ResearchDataUploadBoxEventsConfig):
    """Config needed to publish outbox events"""


def _dto_to_event(dto: ResearchDataUploadBox):
    return dto.model_dump(mode="json")


async def get_box_dao(
    *, config: OutboxPubConfig, dao_publisher_factory: DaoPublisherFactoryProtocol
) -> BoxDao:
    """Construct a ResearchDataUploadBox DAO from the provided dao_factory"""
    if not dao_publisher_factory:
        raise RuntimeError("No DAO Factory and no override provided for BoxDao")

    return await dao_publisher_factory.get_dao(
        name=BOX_COLLECTION,
        dto_model=ResearchDataUploadBox,
        id_field="id",
        autopublish=True,
        dto_to_event=_dto_to_event,
        event_topic=config.research_data_upload_box_topic,
    )
