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
from typing import NamedTuple

import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.jwt_helpers import (
    generate_jwk,
    sign_and_serialize_token,
)
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from pytest import fixture

from ars.config import Config
from ars.ports.inbound.repository import AccessRequestRepositoryPort
from ars.prepare import prepare_consumer, prepare_core, prepare_rest_app

__all__ = [
    "AUTH_CLAIMS_DOE",
    "AUTH_CLAIMS_STEWARD",
    "AUTH_KEY_PAIR",
    "RestFixture",
    "auth_headers_doe_fixture",
    "auth_headers_steward_fixture",
    "consumer_fixture",
    "headers_for_token",
    "rest_fixture",
]

ID_OF_JOHN_DOE = "55203503-8b51-40db-957e-d1781c7fa8ab"
ID_OF_ROD_STEWARD = "4de34d83-f07f-4a93-b3f2-2b0a2c6088ba"
AUTH_KEY_PAIR = generate_jwk()

AUTH_CLAIMS_DOE = {
    "name": "John Doe",
    "email": "john@home.org",
    "title": "Dr.",
    "id": ID_OF_JOHN_DOE,
}

AUTH_CLAIMS_STEWARD = {
    "name": "Rod Steward",
    "email": "steward@ghga.de",
    "id": ID_OF_ROD_STEWARD,
    "roles": ["data_steward@ghga.de"],
}


def headers_for_token(token: str) -> dict[str, str]:
    """Get the Authorization headers for the given token."""
    return {"Authorization": f"Bearer {token}"}


@fixture(name="auth_headers_doe")
def auth_headers_doe_fixture() -> dict[str, str]:
    """Get auth headers for a user requesting access"""
    token = sign_and_serialize_token(AUTH_CLAIMS_DOE, AUTH_KEY_PAIR)
    return headers_for_token(token)


@fixture(name="auth_headers_steward")
def auth_headers_steward_fixture() -> dict[str, str]:
    """Get auth headers for a data steward granting access"""
    token = sign_and_serialize_token(AUTH_CLAIMS_STEWARD, AUTH_KEY_PAIR)
    return headers_for_token(token)


@pytest.fixture(name="config")
def config_fixture(kafka: KafkaFixture, mongodb: MongoDbFixture) -> Config:
    """Fixture for creating a test configuration."""
    return Config(
        auth_key=AUTH_KEY_PAIR.export_public(),  # pyright: ignore
        download_access_url="http://access",
        **kafka.config.model_dump(exclude={"kafka_enable_dlq"}),
        kafka_enable_dlq=True,
        **mongodb.config.model_dump(),
    )


class RestFixture(NamedTuple):
    """Joint fixture object for the REST app."""

    config: Config
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    rest_client: AsyncTestClient


@pytest_asyncio.fixture(name="rest")
async def rest_fixture(
    config: Config, mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[RestFixture]:
    """A fixture that embeds all other fixtures for API-level integration testing."""
    async with prepare_core(config=config) as repository:
        async with (
            prepare_rest_app(config=config, repository_override=repository) as app,
        ):
            async with AsyncTestClient(app=app) as rest_client:
                yield RestFixture(
                    config=config,
                    kafka=kafka,
                    mongodb=mongodb,
                    rest_client=rest_client,
                )


class ConsumerFixture(NamedTuple):
    """Joint fixture object for the REST app."""

    config: Config
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    repository: AccessRequestRepositoryPort
    subscriber: KafkaEventSubscriber


@pytest_asyncio.fixture(name="consumer")
async def consumer_fixture(
    config: Config, mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[ConsumerFixture]:
    """A fixture that embeds all other fixtures for consumer integration testing."""
    async with prepare_consumer(config=config) as consumer:
        yield ConsumerFixture(
            config=config,
            kafka=kafka,
            mongodb=mongodb,
            repository=consumer.repository,
            subscriber=consumer.event_subscriber,
        )
