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
from datetime import timedelta

import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.jwt_helpers import (
    generate_jwk,
    sign_and_serialize_token,
)
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec

from wps.adapters.outbound.dao import (
    get_dataset_dao,
    get_upload_box_dao,
    get_work_package_dao,
)
from wps.config import Config
from wps.core.repository import WorkPackageRepository
from wps.prepare import Consumer, prepare_rest_app

from .access import AccessCheckMock

__all__ = [
    "AUTH_CLAIMS",
    "AUTH_KEY_PAIR",
    "SIGNING_KEY_PAIR",
    "Consumer",
    "fixture_auth_context",
    "fixture_auth_headers",
    "fixture_bad_auth_headers",
    "fixture_client",
    "fixture_config",
    "fixture_repository",
    "headers_for_token",
    "non_mocked_hosts",
]

AUTH_KEY_PAIR = generate_jwk()

SIGNING_KEY_PAIR = generate_jwk()

AUTH_CLAIMS = {
    "name": "John Doe",
    "email": "john@home.org",
    "title": "Dr.",
    "id": "a86f8281-e18a-429e-88a9-a5c8ea0cf754",
}

USER_ID = AUTH_CLAIMS["id"]
RDU_BOX_ID = "91ba4d24-0bb6-4dd4-b80d-b0cf2421fb79"
FILE_BOX_ID = "2d1b33e4-8942-447a-934f-f7a93d95f7e3"


def headers_for_token(token: str) -> dict[str, str]:
    """Get the Authorization headers for the given token."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="auth_headers")
def fixture_auth_headers() -> dict[str, str]:
    """Get auth headers for testing"""
    token = sign_and_serialize_token(AUTH_CLAIMS, AUTH_KEY_PAIR)
    return headers_for_token(token)


@pytest.fixture(name="bad_auth_headers")
def fixture_bad_auth_headers() -> dict[str, str]:
    """Get a invalid auth headers for testing"""
    claims = AUTH_CLAIMS.copy()
    del claims["id"]
    token = sign_and_serialize_token(claims, AUTH_KEY_PAIR)
    return headers_for_token(token)


@pytest.fixture(name="auth_context")
def fixture_auth_context() -> AuthContext:
    """Fixture for getting an auth context"""
    iat = now_utc_ms_prec() - timedelta(
        1
    )  # validity is actually assumed by the repository
    return AuthContext(**AUTH_CLAIMS, iat=iat, exp=iat)  # type: ignore


@pytest.fixture(name="config")
def fixture_config(kafka: KafkaFixture, mongodb: MongoDbFixture) -> Config:
    """Fixture for creating a test configuration."""
    return Config(
        auth_key=AUTH_KEY_PAIR.export_public(),  # pyright: ignore
        access_url="http://access",  # type: ignore
        work_package_signing_key=SIGNING_KEY_PAIR.export_private(),  # pyright: ignore
        **kafka.config.model_dump(exclude={"kafka_enable_dlq"}),
        **mongodb.config.model_dump(),
    )


@pytest_asyncio.fixture(name="repository")
async def fixture_repository(
    config: Config, mongodb: MongoDbFixture
) -> WorkPackageRepository:
    """Fixture for creating a configured repository"""
    dao_factory = mongodb.dao_factory
    work_package_dao = await get_work_package_dao(
        config=config, dao_factory=dao_factory
    )
    upload_box_dao = await get_upload_box_dao(config=config, dao_factory=dao_factory)
    dataset_dao = await get_dataset_dao(config=config, dao_factory=dao_factory)
    return WorkPackageRepository(
        config=config,
        access_check=AccessCheckMock(),
        dataset_dao=dataset_dao,
        upload_box_dao=upload_box_dao,
        work_package_dao=work_package_dao,
    )


@pytest_asyncio.fixture(name="client")
async def fixture_client(config: Config) -> AsyncGenerator[AsyncTestClient, None]:
    """Get test client for the work package service."""
    async with prepare_rest_app(config=config) as app:
        async with AsyncTestClient(app=app) as client:
            yield client


@pytest.fixture
def non_mocked_hosts() -> list[str]:
    """Get hosts that are not mocked by pytest-httpx."""
    return ["test", "localhost"]
