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

from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.jwt_helpers import (
    generate_jwk,
    sign_and_serialize_token,
)
from hexkit.providers.mongodb.testutils import MongoDbFixture
from pytest import fixture
from pytest_asyncio import fixture as async_fixture

from ars.config import Config
from ars.container import Container
from ars.main import (  # pylint: disable=import-outside-toplevel
    get_container,
    get_rest_api,
)

AUTH_KEY_PAIR = generate_jwk()


AUTH_CLAIMS_DOE = {
    "name": "John Doe",
    "email": "john@home.org",
    "title": "Dr.",
    "id": "id-of-john-doe@ghga.de",
    "status": "active",
}

AUTH_CLAIMS_STEWARD = {
    "name": "Rod Steward",
    "email": "steward@ghga.de",
    "id": "id-of-rod-steward@ghga.de",
    "status": "active",
    "role": "data_steward@ghga.de",
}


def headers_for_token(token: str) -> dict[str, str]:
    """Get the Authorization headers for the given token."""
    return {"Authorization": f"Bearer {token}"}


@fixture(name="auth_headers_doe")
def fixture_auth_headers_doe() -> dict[str, str]:
    """Get auth headers for a user requesting access"""
    token = sign_and_serialize_token(AUTH_CLAIMS_DOE, AUTH_KEY_PAIR)
    return headers_for_token(token)


@fixture(name="auth_headers_steward")
def fixture_auth_headers_steward() -> dict[str, str]:
    """Get auth headers for a data steward granting access"""
    token = sign_and_serialize_token(AUTH_CLAIMS_STEWARD, AUTH_KEY_PAIR)
    return headers_for_token(token)


@fixture(name="auth_headers_doe_inactive")
def fixture_auth_headers_doe_inactive() -> dict[str, str]:
    """Get auth headers for an inactive user requesting access"""
    claims_inactive = {**AUTH_CLAIMS_DOE, "status": "inactive"}
    token = sign_and_serialize_token(claims_inactive, AUTH_KEY_PAIR)
    return headers_for_token(token)


@fixture(name="auth_headers_steward_inactive")
def fixture_auth_headers_steward_inactive() -> dict[str, str]:
    """Get auth headers for an inactive data steward granting access"""
    claims_inactive = {**AUTH_CLAIMS_STEWARD, "status": "inactive"}
    token = sign_and_serialize_token(claims_inactive, AUTH_KEY_PAIR)
    return headers_for_token(token)


@async_fixture(name="container")
async def fixture_container(
    mongodb_fixture: MongoDbFixture,
) -> AsyncGenerator[Container, None]:
    """Populate database and get configured container"""

    # create configuration for testing
    config = Config(
        auth_key=AUTH_KEY_PAIR.export_public(),  # pyright: ignore
        **mongodb_fixture.config.dict(),
    )

    async with get_container(config=config) as container:
        # return the configured and wired container
        yield container


@async_fixture(name="client")
async def fixture_client(container: Container) -> AsyncGenerator[AsyncTestClient, None]:
    """Get test client for the access request service"""

    config = container.config()
    api = get_rest_api(config=config)
    async with AsyncTestClient(app=api) as client:
        yield client
