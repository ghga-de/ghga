# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Fixtures for the user registry integration tests"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient as BareClient
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from auth_service.config import Config
from auth_service.deps import get_config
from auth_service.user_management.api.main import app, lifespan


@pytest_asyncio.fixture(name="bare_client")
async def fixture_bare_client(kafka: KafkaFixture) -> AsyncGenerator[BareClient, None]:
    """Get a test client for the user registry without database."""
    config = Config(
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        include_apis=["users"],
    )  # type: ignore
    app.dependency_overrides[get_config] = lambda: config

    async with lifespan(app):
        async with BareClient(app) as client:
            yield client


class FullClient(BareClient):
    """A test client that has been equipped with a database and an event store."""

    config: Config
    mongodb: MongoDbFixture
    kafka: KafkaFixture


@pytest_asyncio.fixture(name="full_client")
async def fixture_full_client(
    mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[FullClient, None]:
    """Get a test client for the user registry with a test database and event store."""
    config = Config(
        db_connection_str=mongodb.config.db_connection_str,
        db_name=mongodb.config.db_name,
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        include_apis=["users"],
    )
    app.dependency_overrides[get_config] = lambda: config
    assert app.router.lifespan_context
    async with lifespan(app):
        async with FullClient(app) as client:
            client.config = config
            client.mongodb = mongodb
            client.kafka = kafka
            yield client
    app.dependency_overrides.clear()
