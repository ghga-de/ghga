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

"""Fixtures that are used in both integration and unit tests"""

from typing import AsyncGenerator

from ghga_service_commons.utils.jwt_helpers import (
    generate_jwk,
    sign_and_serialize_token,
)
from httpx import AsyncClient
from pydantic import SecretStr
from pytest import fixture
from pytest_asyncio import fixture as async_fixture

from wps.config import Config
from wps.main import (  # pylint: disable=import-outside-toplevel
    get_container,
    get_rest_api,
)

AUTH_KEY_PAIR = generate_jwk()

SIGNING_KEY_PAIR = generate_jwk()

AUTH_CLAIMS = {
    "name": "John Doe",
    "email": "john@home.org",
    "title": "Dr.",
    "id": "john-doe@ghga.de",
    "status": "active",
}


def headers_for_token(token: str) -> dict[str, str]:
    """Get the Authorization headers for the given token."""
    return {"Authorization": f"Bearer {token}"}


@fixture(name="auth_headers")
def fixture_auth_headers() -> dict[str, str]:
    """Get auth headers for testing"""
    token = sign_and_serialize_token(AUTH_CLAIMS, AUTH_KEY_PAIR)
    return headers_for_token(token)


@fixture(name="bad_auth_headers")
def fixture_bad_auth_headers() -> dict[str, str]:
    """Get a invalid auth headers for testing"""
    claims = AUTH_CLAIMS.copy()
    claims["status"] = "inactive"
    token = sign_and_serialize_token(claims, AUTH_KEY_PAIR)
    return headers_for_token(token)


@fixture
def non_mocked_hosts() -> list[str]:
    """Get hosts that are not mocked by pytest-httpx."""
    return ["test"]


@async_fixture(name="client")
async def fixture_client(mongodb_fixture) -> AsyncGenerator[AsyncClient, None]:
    """Get test client for the work package service"""

    config = Config(
        auth_key=AUTH_KEY_PAIR.export_public(),
        download_access_url="http://access",
        work_package_signing_key=SecretStr(SIGNING_KEY_PAIR.export_private()),
        **mongodb_fixture.config.dict(),
    )

    async with get_container(config=config):
        api = get_rest_api(config=config)
        async with AsyncClient(app=api, base_url="http://test") as client:
            yield client
