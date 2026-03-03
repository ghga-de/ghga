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

"""Join the functionality of all fixtures for API-level integration testing."""

__all__ = ["JointFixture", "joint_fixture"]
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import httpx
import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.testing.dao import new_mock_dao_class

from dins.adapters.outbound.dao import get_dataset_dao, get_file_information_dao
from dins.config import Config
from dins.core.information_service import InformationService
from dins.core.models import (
    DatasetFileAccessions,
    FileAccessionMap,
    FileInformation,
    PendingFileInfo,
)
from dins.inject import (
    prepare_core,
    prepare_event_subscriber,
    prepare_rest_app,
)
from dins.ports.inbound.dao import (
    DatasetDaoPort,
    FileAccessionMapDaoPort,
    FileInformationDaoPort,
    PendingFileInfoDaoPort,
)
from dins.ports.inbound.information_service import InformationServicePort
from tests.fixtures.config import get_config

InMemFileInformationDao: type[FileInformationDaoPort] = new_mock_dao_class(  # type: ignore
    dto_model=FileInformation, id_field="accession"
)
InMemAccessionMapDao: type[FileAccessionMapDaoPort] = new_mock_dao_class(  # type: ignore
    dto_model=FileAccessionMap, id_field="accession"
)
InMemPendingFileInfoDao: type[PendingFileInfoDaoPort] = new_mock_dao_class(  # type: ignore
    dto_model=PendingFileInfo, id_field="file_id"
)
InMemDatasetDao: type[DatasetDaoPort] = new_mock_dao_class(  # type: ignore
    dto_model=DatasetFileAccessions, id_field="accession"
)


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    information_service: InformationServicePort
    dataset_dao: DatasetDaoPort
    file_information_dao: FileInformationDaoPort
    rest_client: httpx.AsyncClient
    event_subscriber: KafkaEventSubscriber
    mongodb: MongoDbFixture
    kafka: KafkaFixture


@pytest_asyncio.fixture
async def joint_fixture(
    mongodb: MongoDbFixture,
    kafka: KafkaFixture,
) -> AsyncGenerator[JointFixture]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    config = get_config(
        sources=[
            mongodb.config,
            kafka.config,
        ],
        kafka_enable_dlq=True,
    )

    # prepare everything except the outbox subscriber
    async with (
        prepare_core(config=config) as information_service,
        prepare_rest_app(
            config=config, information_service_override=information_service
        ) as app,
        prepare_event_subscriber(
            config=config, information_service_override=information_service
        ) as event_subscriber,
        AsyncTestClient(app=app) as rest_client,
    ):
        file_information_dao = await get_file_information_dao(
            dao_factory=mongodb.dao_factory
        )
        dataset_dao = await get_dataset_dao(dao_factory=mongodb.dao_factory)
        yield JointFixture(
            config=config,
            information_service=information_service,
            dataset_dao=dataset_dao,
            file_information_dao=file_information_dao,
            rest_client=rest_client,
            event_subscriber=event_subscriber,
            mongodb=mongodb,
            kafka=kafka,
        )


@dataclass
class JointRig:
    """A smaller version of JointFixture designed for unit testing"""

    information_service: InformationServicePort
    file_information_dao: FileInformationDaoPort
    accession_map_dao: FileAccessionMapDaoPort
    pending_file_info_dao: PendingFileInfoDaoPort
    dataset_dao: DatasetDaoPort


@pytest.fixture
def rig() -> JointRig:
    """Produce a populated JointRig instance"""
    file_information_dao = InMemFileInformationDao()
    accession_map_dao = InMemAccessionMapDao()
    pending_file_info_dao = InMemPendingFileInfoDao()
    dataset_dao = InMemDatasetDao()
    information_service = InformationService(
        file_information_dao=file_information_dao,
        accession_map_dao=accession_map_dao,
        pending_file_info_dao=pending_file_info_dao,
        dataset_dao=dataset_dao,
    )
    return JointRig(
        file_information_dao=file_information_dao,
        accession_map_dao=accession_map_dao,
        pending_file_info_dao=pending_file_info_dao,
        dataset_dao=dataset_dao,
        information_service=information_service,
    )
