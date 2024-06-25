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
"""Adapter for publishing outbox events to other services."""

from ghga_event_schemas.pydantic_ import NonStagedFileRequested
from hexkit.protocols.daopub import DaoPublisher, DaoPublisherFactoryProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from dcs.ports.outbound.daopub import OutboxPublisherFactoryPort


class OutboxDaoConfig(BaseSettings):
    """Configuration for the outbox DAO and publishing events"""

    unstaged_download_event_topic: str = Field(
        default=...,
        description=(
            "Name of the topic used for events indicating that a download was requested"
            + " for a file that is not yet available in the outbox."
        ),
        examples=["file_downloads"],
    )
    unstaged_download_collection: str = Field(
        default=...,
        description=(
            "The type used for event indicating that a download was requested"
            + " for a file that is not yet available in the outbox. The"
            + " value should use hyphens in place of underscores if needed."
        ),
        examples=["unstaged-download-requested"],
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
        self._unstaged_download_collection = config.unstaged_download_collection
        self._unstaged_download_event_topic = config.unstaged_download_event_topic

    async def get_nonstaged_file_requested_dao(
        self,
    ) -> DaoPublisher[NonStagedFileRequested]:
        """Construct a DAO for interacting with successful file validation events in the DB.

        This DAO automatically publishes changes as events.
        """
        return await self._dao_publisher_factory.get_dao(
            name=self._unstaged_download_collection,
            dto_model=NonStagedFileRequested,
            id_field="file_id",
            dto_to_event=lambda event: event.model_dump(),
            event_topic=self._unstaged_download_event_topic,
            autopublish=True,
        )
