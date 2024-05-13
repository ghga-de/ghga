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

"""Fixtures for the claims repository integration tests"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient as BareClient
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from auth_service.config import Config
from auth_service.deps import get_config, get_mongodb_dao_factory
from auth_service.user_management.api.main import app, lifespan
from auth_service.user_management.user_registry.models.users import User, UserStatus


@pytest_asyncio.fixture(name="bare_client")
async def fixture_bare_client() -> AsyncGenerator[BareClient, None]:
    """Get a test client for the claims repository without a database connection."""
    config = Config(
        include_apis=["claims"],
    )  # type: ignore
    app.dependency_overrides[get_config] = lambda: config
    async with lifespan(app):
        async with BareClient(app) as client:
            yield client


data_steward = User(
    id="the-id-of-rod-steward",
    ext_id="rod@ls.org",
    name="Rod Steward",
    email="rod@example.org",
    status=UserStatus.ACTIVE,
    registration_date=now_as_utc(),
)

add_as_data_stewards = [data_steward.ext_id]


async def seed_database(config: Config) -> None:
    """Seed the database with a dummy user that will become a data steward."""
    user_dao = await get_mongodb_dao_factory(config=config).get_dao(
        name=config.users_collection,
        dto_model=User,
        id_field="id",
    )
    try:
        await user_dao.get_by_id(data_steward.id)
    except ResourceNotFoundError:
        await user_dao.insert(data_steward)


class FullClient(BareClient):
    """A test client that has been equipped with a database."""

    mongodb: MongoDbFixture


@pytest_asyncio.fixture(name="full_client")
async def fixture_full_client(
    mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[FullClient, None]:
    """Get a test client for the user registry with a test database."""
    config = Config(
        db_connection_str=mongodb.config.db_connection_str,
        db_name=mongodb.config.db_name,
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        include_apis=["claims"],
        add_as_data_stewards=add_as_data_stewards,  # type: ignore
    )  # pyright: ignore
    await seed_database(config)
    app.dependency_overrides[get_config] = lambda: config
    async with lifespan(app):
        async with FullClient(app) as client:
            yield client
    app.dependency_overrides.clear()
