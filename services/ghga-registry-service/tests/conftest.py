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
"""Test fixture setup"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.auth.ghga import AuthConfig
from ghga_service_commons.utils import jwt_helpers
from hexkit.providers.akafka.testutils import (  # noqa: F401
    kafka_container_fixture,
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    mongodb_container_fixture,
    mongodb_fixture,
)
from jwcrypto.jwk import JWK

from rs.config import Config
from rs.inject import prepare_rest_app
from tests.fixtures import AppFixture
from tests.fixtures.config import get_config
from tests.fixtures.joint import joint_fixture

__all__ = ["joint_fixture"]


@pytest.fixture(name="_hidden_fixture")
def config_plus_jwk_setup() -> tuple[Config, JWK]:
    """Background/setup fixture that produces a Config class alongside the pub/sec JWK."""
    uos_jwk = jwt_helpers.generate_jwk()
    uos_auth_key = uos_jwk.export(private_key=False)
    uos_cfg = AuthConfig(auth_key=uos_auth_key, auth_check_claims={})
    config = get_config(uos_auth_config=uos_cfg)
    return (config, uos_jwk)


@pytest.fixture(name="config")
def config_fixture(_hidden_fixture: tuple[Config, JWK]) -> Config:
    """Automatic test config setup"""
    return _hidden_fixture[0]


@pytest.fixture(name="uos_jwk")
def uos_jwk_fixture(_hidden_fixture: tuple[Config, JWK]) -> JWK:
    """Returns the UOS JWK used to create the test config"""
    return _hidden_fixture[1]


@pytest_asyncio.fixture()
async def app_fixture(config: Config) -> AsyncGenerator[AppFixture]:
    """A fixture that yields a configured rest client and accessible core override"""
    core_mock = AsyncMock()
    async with (
        prepare_rest_app(config=config, core_override=core_mock) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield AppFixture(rest_client=rest_client, core_mock=core_mock)
