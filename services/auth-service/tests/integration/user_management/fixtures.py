# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Fixtures for the user management integration tests"""

from typing import Generator

from fastapi.testclient import TestClient
from pytest import fixture
from testcontainers.mongodb import MongoDbContainer

from auth_service.config import Config
from auth_service.deps import get_config
from auth_service.user_management.api.main import app


@fixture(name="client")
def fixture_client() -> TestClient:
    """Get test client for the user manager"""
    return TestClient(app)


@fixture(name="client_with_db")
def fixture_client_with_db() -> Generator[TestClient, None, None]:
    """Get test client for the user manager with a test database."""

    with MongoDbContainer() as mongodb:
        connection_url = mongodb.get_connection_url()
        config = Config(db_url=connection_url, db_name="test-user-management")

        app.dependency_overrides[get_config] = lambda: config
        yield TestClient(app)
        app.dependency_overrides.clear()
