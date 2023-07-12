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

"""Joint fixture"""
from dataclasses import dataclass
from typing import AsyncGenerator

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient

from tests.fixtures.config import get_config
from wkvs.config import Config
from wkvs.container import Container
from wkvs.main import get_configured_container, get_rest_api


@dataclass
class JointFixture:
    config: Config
    container: Container
    rest_client: AsyncTestClient


@pytest_asyncio.fixture
async def joint_fixture() -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""

    config = get_config()

    # create a DI container instance
    container = get_configured_container(config=config)
    container.wire(modules=["wkvs.adapters.inbound.fastapi_.routes"])

    # setup an API test client:
    api = get_rest_api(config=config)
    async with AsyncTestClient(app=api) as rest_client:
        yield JointFixture(
            config=config,
            container=container,
            rest_client=rest_client,
        )
