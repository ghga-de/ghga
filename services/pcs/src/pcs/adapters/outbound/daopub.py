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
"""Outbox-pattern DAO to communicate database state via kafka."""

from ghga_event_schemas.configs import FileDeletionRequestEventsConfig
from ghga_event_schemas.pydantic_ import FileDeletionRequested
from hexkit.protocols.daopub import DaoPublisher, DaoPublisherFactoryProtocol
from pydantic import Field

from pcs.ports.outbound.daopub import OutboxPublisherFactoryPort

__all__ = ["OutboxDaoConfig", "OutboxDaoPublisherFactory"]


class OutboxDaoConfig(FileDeletionRequestEventsConfig):
    """Configuration for the outbox DAO and publishing events"""

    file_deletions_collection: str = Field(
        default="fileDeletions",
        description="The name of the collection used to store file deletion requests.",
        examples=["fileDeletions"],
    )


class OutboxDaoPublisherFactory(OutboxPublisherFactoryPort):
    """Translation between OutboxDaoPublisherFactoryPort and DaoPublisherFactoryProtocol."""

    def __init__(
        self,
        *,
        config: OutboxDaoConfig,
        dao_publisher_factory: DaoPublisherFactoryProtocol,
    ) -> None:
        """Configure with provider for the DaoFactoryProtocol"""
        self._dao_publisher_factory = dao_publisher_factory
        self._file_deletions_collection = config.file_deletions_collection
        self._file_deletion_topic = config.file_deletion_request_topic

    async def get_file_deletion_dao(self) -> DaoPublisher[FileDeletionRequested]:
        """Construct a DAO for interacting with file deletion requests in the database.

        This DAO automatically publishes changes as events.
        """
        return await self._dao_publisher_factory.get_dao(
            name=self._file_deletions_collection,
            dto_model=FileDeletionRequested,
            id_field="file_id",
            dto_to_event=lambda event: event.model_dump(),
            event_topic=self._file_deletion_topic,
            autopublish=True,
        )
