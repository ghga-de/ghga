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

from importlib import reload
from os import environ
from typing import Generator

from fastapi.testclient import TestClient
from pytest import fixture

from auth_service import config
from auth_service.auth_adapter.api import main


@fixture(name="client")
def fixture_client() -> Generator[TestClient, None, None]:
    """Get test client for the auth adapter"""
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@fixture(name="with_basic_auth")
def fixture_with_basic_auth() -> Generator[str, None, None]:
    """Run test with Basic authentication"""
    user, pwd = "testuser", "testpwd"
    environ["AUTH_SERVICE_BASIC_AUTH_USER"] = user
    environ["AUTH_SERVICE_BASIC_AUTH_PWD"] = pwd
    reload(config)
    reload(main)
    yield f"{user}:{pwd}"
    del environ["AUTH_SERVICE_BASIC_AUTH_USER"]
    del environ["AUTH_SERVICE_BASIC_AUTH_PWD"]
    reload(config)
    reload(main)
