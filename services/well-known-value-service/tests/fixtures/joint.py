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

"""Joint fixture"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient

from tests.fixtures.config import get_config
from wkvs.config import Config
from wkvs.inject import prepare_rest_app


@dataclass
class JointFixture:
    """Joint fixture for testing"""

    config: Config
    rest_client: AsyncTestClient


@pytest_asyncio.fixture
async def joint_fixture() -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    config = get_config()

    async with prepare_rest_app(config=config) as app:
        async with AsyncTestClient(app=app) as rest_client:
            yield JointFixture(
                config=config,
                rest_client=rest_client,
            )
