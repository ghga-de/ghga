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

"""A fixture that consolidates service components and test fixtures into one class"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from dlqs.config import Config
from dlqs.inject import prepare_core, prepare_rest_app
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from tests.fixtures.config import get_config


@dataclass
class JointFixture:
    """Joint fixture class"""

    config: Config
    dlq_manager: DLQManagerPort
    rest_client: AsyncTestClient
    kafka: KafkaFixture


@pytest_asyncio.fixture
async def joint_fixture(
    kafka: KafkaFixture, mongodb: MongoDbFixture
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    config = get_config([kafka.config, mongodb.config])

    async with (
        prepare_core(config=config) as dlq_manager,
        prepare_rest_app(config=config, dlq_manager_override=dlq_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield JointFixture(
            config=config,
            dlq_manager=dlq_manager,
            rest_client=rest_client,
            kafka=kafka,
        )
