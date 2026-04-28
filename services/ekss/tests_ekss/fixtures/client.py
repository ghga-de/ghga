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

"""Fixtures that are used in both integration and unit tests"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient

from ekss.inject import prepare_rest_app
from ekss.ports.inbound.secrets import SecretsHandlerPort
from tests_ekss.fixtures.config import get_config


@dataclass
class ClientFixture:
    """Fixture providing a configured rest client and access to the SecretsHandler mock"""

    client: AsyncTestClient
    secrets_handler: SecretsHandlerPort


@pytest_asyncio.fixture()
async def client_fixture() -> AsyncGenerator[ClientFixture]:
    """Yields a configured client with a mocked SecretsHandler"""
    config = get_config()
    secrets_handler_mock = AsyncMock(spec=SecretsHandlerPort)
    async with (
        prepare_rest_app(
            config=config, secrets_handler_override=secrets_handler_mock
        ) as app,
        AsyncTestClient(app=app) as client,
    ):
        yield ClientFixture(client=client, secrets_handler=secrets_handler_mock)
