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
#
"""Bundle test fixtures together"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.testing.dao import new_mock_dao_class
from hexkit.providers.testing.eventpub import InMemEventPublisher, InMemEventStore

from fis.adapters.outbound.event_pub import EventPubTranslator
from fis.config import Config
from fis.core.interrogation import InterrogationHandler
from fis.core.models import FileUnderInterrogation, InterrogationReport
from fis.inject import prepare_core, prepare_event_subscriber, prepare_rest_app
from fis.ports.inbound.interrogation import InterrogationHandlerPort
from fis.ports.outbound.dao import FileDao, InterrogationReportDao
from fis.ports.outbound.event_pub import EventPubTranslatorPort
from fis.ports.outbound.secrets import SecretsClientPort
from tests_fis.fixtures.config import get_config

__all__ = ["JointFixture", "joint_fixture"]

InMemFileDao: type[FileDao] = new_mock_dao_class(
    dto_model=FileUnderInterrogation, id_field="id"
)

InMemInterrogationReportDao: type[InterrogationReportDao] = new_mock_dao_class(
    dto_model=InterrogationReport, id_field="file_id"
)


@dataclass
class JointFixture:
    """A test class that holds the main components of the service for testing"""

    config: Config
    kafka: KafkaFixture
    file_dao: FileDao
    rest_client: httpx.AsyncClient
    outbox_consumer: KafkaEventSubscriber
    interrogation_handler: InterrogationHandlerPort


@pytest_asyncio.fixture
async def joint_fixture(
    kafka: KafkaFixture, mongodb: MongoDbFixture
) -> AsyncGenerator[JointFixture]:
    """Set up fixture with testcontainer config spliced in"""
    config = get_config(sources=[kafka.config, mongodb.config])

    async with (
        prepare_core(config=config) as interrogation_handler,
        prepare_rest_app(config=config, core_override=interrogation_handler) as app,
        prepare_event_subscriber(
            config=config, core_override=interrogation_handler
        ) as outbox_consumer,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield JointFixture(
            config=config,
            kafka=kafka,
            file_dao=interrogation_handler._file_dao,
            rest_client=rest_client,
            outbox_consumer=outbox_consumer,
            interrogation_handler=interrogation_handler,
        )


@dataclass
class JointRig:
    """A smaller version of JointFixture designed for unit testing"""

    config: Config
    file_dao: FileDao
    interrogation_report_dao: InterrogationReportDao
    secrets_client: AsyncMock
    publisher: EventPubTranslatorPort
    event_store: InMemEventStore
    interrogation_handler: InterrogationHandlerPort


@pytest.fixture
def rig(config: Config) -> JointRig:
    """Produce a populated JointRig instance"""
    event_store = InMemEventStore()
    file_dao = InMemFileDao()
    interrogation_report_dao = InMemInterrogationReportDao()
    secrets_client = AsyncMock(spec=SecretsClientPort)
    secrets_client.deposit_secret.return_value = "mock-secret-id"
    publisher = EventPubTranslator(
        config=config, provider=InMemEventPublisher(event_store)
    )
    interrogation_handler = InterrogationHandler(
        config=config,
        file_dao=file_dao,
        interrogation_report_dao=interrogation_report_dao,
        event_publisher=publisher,
        secrets_client=secrets_client,
    )
    return JointRig(
        config=config,
        file_dao=file_dao,
        interrogation_report_dao=interrogation_report_dao,
        secrets_client=secrets_client,
        publisher=publisher,
        event_store=event_store,
        interrogation_handler=interrogation_handler,
    )
