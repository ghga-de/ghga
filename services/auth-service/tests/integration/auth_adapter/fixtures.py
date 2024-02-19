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

"""Fixtures for the auth adapter integration tests"""

from collections.abc import AsyncGenerator, Generator
from importlib import reload
from os import environ

from ghga_service_commons.api.testing import AsyncTestClient
from pytest import fixture
from pytest_asyncio import fixture as async_fixture


@async_fixture(name="client")
async def fixture_client() -> AsyncGenerator[AsyncTestClient, None]:
    """Get test client for the auth adapter"""
    from auth_service import config
    from auth_service.auth_adapter.api import main

    environ["AUTH_SERVICE_ALLOW_READ_PATHS"] = '["/allowed/read/*", "/logo.png"]'
    environ["AUTH_SERVICE_ALLOW_WRITE_PATHS"] = '["/allowed/write/*"]'
    reload(config)
    reload(main)
    async with AsyncTestClient(main.app) as client:
        yield client
    del environ["AUTH_SERVICE_ALLOW_READ_PATHS"]
    del environ["AUTH_SERVICE_ALLOW_WRITE_PATHS"]
    reload(config)
    reload(main)


@fixture(name="with_basic_auth")
def fixture_with_basic_auth() -> Generator[str, None, None]:
    """Run test with Basic authentication"""
    from auth_service import config
    from auth_service.auth_adapter.api import main

    user, pwd = "testuser", "testpwd"
    credentials = f"{user}:{pwd}"
    environ["AUTH_SERVICE_BASIC_AUTH_CREDENTIALS"] = credentials
    reload(config)
    reload(main)
    yield credentials
    del environ["AUTH_SERVICE_BASIC_AUTH_CREDENTIALS"]
    reload(config)
    reload(main)
