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

import httpx
import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils import jwt_helpers
from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token
from hexkit.correlation import set_new_correlation_id
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
from tests.fixtures.utils import DS_AUTH_CLAIMS, USER_AUTH_CLAIMS, headers_for_token

__all__ = ["joint_fixture"]


class _HiddenFixture:
    def __init__(self, config: Config, auth_jwk: JWK, work_order_jwk: JWK) -> None:
        self.config = config
        self.auth_jwk = auth_jwk
        self.work_order_jwk = work_order_jwk


@pytest.fixture(name="_hidden_fixture")
def config_plus_jwk_setup() -> _HiddenFixture:
    """Background/setup fixture that produces a Config class alongside the auth JWK."""
    auth_jwk = jwt_helpers.generate_jwk()  # This is for inbound requests
    auth_key = auth_jwk.export(private_key=False)
    work_order_signing_jwk = jwt_helpers.generate_jwk()  # This is for outbound requests
    work_order_signing_key = work_order_signing_jwk.export(private_key=True)
    config = get_config(
        auth_key=auth_key, work_order_signing_key=work_order_signing_key
    )
    return _HiddenFixture(config, auth_jwk, work_order_signing_jwk)


@pytest.fixture(name="config")
def config_fixture(_hidden_fixture: _HiddenFixture) -> Config:
    """Automatic test config setup"""
    return _hidden_fixture.config


@pytest.fixture(name="auth_jwk")
def auth_jwk_fixture(_hidden_fixture: _HiddenFixture) -> JWK:
    """Returns the auth JWK used to create the test config"""
    return _hidden_fixture.auth_jwk


@pytest.fixture(name="work_order_jwk")
def work_order_jwk_fixture(_hidden_fixture: _HiddenFixture) -> JWK:
    """Returns the work order JWK used to create the test config"""
    return _hidden_fixture.work_order_jwk


@pytest_asyncio.fixture()
async def app_fixture(config: Config) -> AsyncGenerator[AppFixture]:
    """A fixture that yields a configured rest client and accessible core override"""
    core_mock = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=core_mock) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield AppFixture(rest_client=rest_client, core_mock=core_mock)


@pytest_asyncio.fixture()
async def httpx_client() -> AsyncGenerator[httpx.AsyncClient]:
    """Yields an AsyncClient"""
    async with httpx.AsyncClient() as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def cid_fixture():
    async with set_new_correlation_id() as cid:
        yield cid


@pytest.fixture(name="user_auth_headers")
def fixture_user_auth_headers(auth_jwk: JWK) -> dict[str, str]:
    """Get auth headers for testing"""
    token = sign_and_serialize_token(USER_AUTH_CLAIMS, auth_jwk)
    return headers_for_token(token)


@pytest.fixture(name="ds_auth_headers")
def fixture_ds_auth_headers(auth_jwk: JWK) -> dict[str, str]:
    """Get auth headers for testing"""
    token = sign_and_serialize_token(DS_AUTH_CLAIMS, auth_jwk)
    return headers_for_token(token)


@pytest.fixture(name="bad_auth_headers")
def fixture_bad_auth_headers(auth_jwk: JWK) -> dict[str, str]:
    """Get a invalid auth headers for testing"""
    claims = DS_AUTH_CLAIMS.copy()
    del claims["id"]
    token = sign_and_serialize_token(claims, auth_jwk)
    return headers_for_token(token)
