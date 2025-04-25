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

"""Fixtures for the user registry integration tests"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient as BareClient
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from auth_service.config import Config
from auth_service.prepare import prepare_rest_app


@pytest_asyncio.fixture(name="bare_client")
async def fixture_bare_client(kafka: KafkaFixture) -> AsyncGenerator[BareClient, None]:
    """Get a test client for the user registry without database."""
    config = Config(
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        provide_apis=["users"],
    )  # type: ignore
    async with prepare_rest_app(config) as app, BareClient(app) as client:
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
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        provide_apis=["users"],
    )
    async with prepare_rest_app(config) as app, FullClient(app) as client:
        client.config = config
        client.mongodb = mongodb
        client.kafka = kafka
        yield client
