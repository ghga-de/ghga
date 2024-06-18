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
#
"""Join the functionality of all fixtures for API-level integration testing."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import httpx
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.simple_token import generate_token_and_hash
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongokafka.testutils import MongoKafkaFixture

from pcs.adapters.inbound.fastapi_.config import TokenHashConfig
from pcs.config import Config
from pcs.inject import get_file_deletion_dao, prepare_core, prepare_rest_app
from pcs.ports.inbound.file_deletion import FileDeletionPort
from pcs.ports.outbound.daopub import FileDeletionDao
from tests_pcs.fixtures.config import get_config

__all__ = ["joint_fixture", "JointFixture"]


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    dao: FileDeletionDao
    file_deletion: FileDeletionPort
    rest_client: httpx.AsyncClient
    kafka: KafkaFixture
    mongo_kafka: MongoKafkaFixture
    token: str


@pytest_asyncio.fixture
async def joint_fixture(
    mongo_kafka: MongoKafkaFixture,
    kafka: KafkaFixture,
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    token, hash = generate_token_and_hash()

    token_hash_config = TokenHashConfig(token_hashes=[hash])
    config = get_config(sources=[mongo_kafka.config, kafka.config, token_hash_config])
    async with (
        get_file_deletion_dao(config=config) as dao,
        prepare_core(config=config) as file_deletion,
        prepare_rest_app(config=config, core_override=file_deletion) as app,
    ):
        async with AsyncTestClient(app=app) as rest_client:
            yield JointFixture(
                config=config,
                dao=dao,
                file_deletion=file_deletion,
                rest_client=rest_client,
                mongo_kafka=mongo_kafka,
                kafka=kafka,
                token=token,
            )
