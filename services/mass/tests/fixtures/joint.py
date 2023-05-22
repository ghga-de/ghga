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

"""Provides multiple fixtures in one spot, with a mongodb fixture that comes pre-populated"""
# pylint: disable=unused-import, redefined-outer-name

from dataclasses import dataclass
from typing import AsyncGenerator

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    MongoDbFixture,
    mongodb_fixture,
)

from mass.config import Config
from mass.container import Container
from mass.main import get_configured_container, get_rest_api
from tests.fixtures.config import get_config
from tests.fixtures.mongo import populated_mongodb_fixture  # noqa: F401


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    container: Container
    mongodb: MongoDbFixture
    rest_client: AsyncTestClient


@pytest_asyncio.fixture
async def joint_fixture(
    populated_mongodb_fixture: MongoDbFixture,  # noqa: F811
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""

    # merge configs from different sources with the default one:
    config = get_config(sources=[populated_mongodb_fixture.config])

    # create a DI container instance:translators
    async with get_configured_container(config=config) as container:
        container.wire(modules=["mass.adapters.inbound.fastapi_.routes"])

        # setup an API test client:
        api = get_rest_api(config=config)
        async with AsyncTestClient(app=api) as rest_client:
            yield JointFixture(
                config=config,
                container=container,
                mongodb=populated_mongodb_fixture,
                rest_client=rest_client,
            )
