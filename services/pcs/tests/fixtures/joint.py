# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from hexkit.providers.akafka.testutils import KafkaFixture, kafka_fixture
from pcs.adapters.inbound.fastapi_.config import TokenHashConfig
from pcs.config import Config
from pcs.inject import prepare_core, prepare_rest_app
from pcs.ports.inbound.file_deletion import FileDeletionPort

from tests.fixtures.config import get_config

__all__ = [
    "joint_fixture",
    "JointFixture",
    "kafka_fixture",
]


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    file_deletion: FileDeletionPort
    rest_client: httpx.AsyncClient
    kafka: KafkaFixture
    token: str


@pytest_asyncio.fixture
async def joint_fixture(
    kafka_fixture: KafkaFixture,
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    token, hash = generate_token_and_hash()

    token_hash_config = TokenHashConfig(token_hashes=[hash])

    config = get_config(sources=[kafka_fixture.config, token_hash_config])

    async with prepare_core(config=config) as file_deletion:
        async with prepare_rest_app(config=config, core_override=file_deletion) as app:
            async with AsyncTestClient(app=app) as rest_client:
                yield JointFixture(
                    config=config,
                    file_deletion=file_deletion,
                    rest_client=rest_client,
                    kafka=kafka_fixture,
                    token=token,
                )
