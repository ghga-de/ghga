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

"""Bundle different test fixtures into one fixture"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from rts.adapters.outbound.dao import get_metadata_dao
from rts.config import Config
from rts.inject import prepare_core, prepare_event_subscriber, prepare_rest_app
from rts.ports.inbound.rev_tran import ReverseTranspilerPort
from rts.ports.outbound.dao import MetadataDao
from tests.fixtures.config import get_config


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    reverse_transpiler: ReverseTranspilerPort
    event_subscriber: KafkaEventSubscriber
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    metadata_dao: MetadataDao
    rest_client: AsyncTestClient


@pytest_asyncio.fixture(scope="function")
async def joint_fixture(
    mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing

    **Do not call directly** Instead, use get_joint_fixture().
    """
    # merge configs from different sources with the default one
    config = get_config(sources=[mongodb.config, kafka.config], kafka_enable_dlq=True)

    # Knit together the components into the joint fixture
    async with (
        prepare_core(config=config) as reverse_transpiler,
        prepare_rest_app(
            config=config, reverse_transpiler_override=reverse_transpiler
        ) as app,
        AsyncTestClient(app=app) as rest_client,
        prepare_event_subscriber(
            config=config, reverse_transpiler_override=reverse_transpiler
        ) as event_subscriber,
    ):
        yield JointFixture(
            config=config,
            reverse_transpiler=reverse_transpiler,
            event_subscriber=event_subscriber,
            kafka=kafka,
            mongodb=mongodb,
            metadata_dao=await get_metadata_dao(dao_factory=mongodb.dao_factory),
            rest_client=rest_client,
        )
