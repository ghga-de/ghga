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

from collections.abc import AsyncGenerator, Generator

from ghga_service_commons.api.testing import AsyncTestClient
from pydantic import SecretStr
from pytest import fixture
from pytest_asyncio import fixture as async_fixture
from testcontainers.mongodb import MongoDbContainer

from auth_service.config import Config
from auth_service.deps import get_config
from auth_service.user_management.api.main import app, lifespan


@async_fixture(name="client")
async def fixture_client() -> AsyncGenerator[AsyncTestClient, None]:
    """Get a test client for the user registry."""
    config = Config(
        include_apis=["users"],
    )  # type: ignore
    app.dependency_overrides[get_config] = lambda: config
    async with lifespan(app):
        async with AsyncTestClient(app) as client:
            yield client


@fixture(name="mongodb", scope="session")
def fixture_mongodb() -> Generator[MongoDbContainer, None, None]:
    """Get a test container for the Mongo database."""
    with MongoDbContainer() as mongodb:
        yield mongodb


@async_fixture(name="client_with_db")
async def fixture_client_with_db(
    mongodb: MongoDbContainer,
) -> AsyncGenerator[AsyncTestClient, None]:
    """Get a test client for the user registry with a test database."""
    config = Config(
        db_connection_str=SecretStr(mongodb.get_connection_url()),
        db_name="test-user-registry",
        include_apis=["users"],
    )  # type: ignore
    mongodb.get_connection_client().drop_database(config.db_name)
    app.dependency_overrides[get_config] = lambda: config
    assert app.router.lifespan_context
    async with lifespan(app):
        async with AsyncTestClient(app) as client:
            yield client
    app.dependency_overrides.clear()
