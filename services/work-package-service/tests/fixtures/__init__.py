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

import asyncio
from collections.abc import AsyncGenerator
from datetime import timedelta

from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.jwt_helpers import (
    generate_jwk,
    sign_and_serialize_token,
)
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from pytest import fixture
from pytest_asyncio import fixture as async_fixture

from wps.adapters.outbound.dao import DatasetDaoConstructor, WorkPackageDaoConstructor
from wps.config import Config
from wps.container import Container
from wps.core.repository import WorkPackageConfig, WorkPackageRepository
from wps.main import get_container, get_rest_api

from .access import AccessCheckMock
from .datasets import DATASET_UPSERTION_EVENT

__all__ = [
    "AUTH_CLAIMS",
    "AUTH_KEY_PAIR",
    "SIGNING_KEY_PAIR",
    "fixture_auth_context",
    "fixture_auth_headers",
    "fixture_bad_auth_headers",
    "fixture_client",
    "fixture_container",
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


@fixture(name="auth_context")
def fixture_auth_context() -> AuthContext:
    """Fixture for getting an auth context"""
    iat = now_as_utc() - timedelta(1)  # validity is actually assumed by the repository
    return AuthContext(**AUTH_CLAIMS, iat=iat, exp=iat)  # pyright: ignore


@async_fixture(name="repository")
async def fixture_repository(mongodb_fixture: MongoDbFixture) -> WorkPackageRepository:
    """Fixture for creating a configured repository"""
    work_package_config = WorkPackageConfig(
        work_package_signing_key=SIGNING_KEY_PAIR.export_private()  # type: ignore
    )
    dataset_dao = await DatasetDaoConstructor.construct(
        config=work_package_config,
        dao_factory=mongodb_fixture.dao_factory,
    )
    work_package_dao = await WorkPackageDaoConstructor.construct(
        config=work_package_config,
        dao_factory=mongodb_fixture.dao_factory,
    )
    repository = WorkPackageRepository(
        config=work_package_config,
        access_check=AccessCheckMock(),
        dataset_dao=dataset_dao,
        work_package_dao=work_package_dao,
    )
    return repository


@async_fixture(name="container")
async def fixture_container(
    mongodb_fixture: MongoDbFixture, kafka_fixture: KafkaFixture
) -> AsyncGenerator[Container, None]:
    """Populate database and get configured container"""

    # create configuration for testing
    config = Config(
        auth_key=AUTH_KEY_PAIR.export_public(),  # pyright: ignore
        download_access_url="http://access",
        work_package_signing_key=SIGNING_KEY_PAIR.export_private(),  # pyright: ignore
        **kafka_fixture.config.dict(),
        **mongodb_fixture.config.dict(),
    )

    # publish an event announcing a dataset
    async with get_container(config=config) as container:
        await kafka_fixture.publish_event(
            payload=DATASET_UPSERTION_EVENT.dict(),
            topic=config.dataset_change_event_topic,
            type_=config.dataset_upsertion_event_type,
            key="test-key-fixture",
        )

        # populate database with published dataset
        event_subscriber = await container.event_subscriber()
        # wait for event to be submitted and processed
        await asyncio.wait_for(event_subscriber.run(forever=False), timeout=10)
        await asyncio.sleep(0.25)

        # return the configured and wired container
        yield container


@async_fixture(name="client")
async def fixture_client(container: Container) -> AsyncGenerator[AsyncTestClient, None]:
    """Get test client for the work package service"""

    config = container.config()
    api = get_rest_api(config=config)
    async with AsyncTestClient(app=api) as client:
        yield client


@fixture
def non_mocked_hosts() -> list[str]:
    """Get hosts that are not mocked by pytest-httpx."""
    return ["test", "localhost"]
