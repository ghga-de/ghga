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

"""Fixtures for the auth adapter integration tests"""

import json
from collections.abc import AsyncGenerator
from datetime import timedelta
from importlib import reload
from typing import NamedTuple

import pytest_asyncio
from fastapi import status
from ghga_service_commons.api.testing import AsyncTestClient as BareClient
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.akafka.testutils import KafkaFixture
from httpx import Response
from pydantic import SecretStr
from pytest_httpx import HTTPXMock

from auth_service import config as config_module
from auth_service.auth_adapter import prepare as auth_adapter_prepare_module
from auth_service.auth_adapter.core.session_store import Session
from auth_service.auth_adapter.core.totp import TOTPHandler
from auth_service.auth_adapter.deps import SESSION_COOKIE, get_user_token_dao
from auth_service.auth_adapter.prepare import prepare_rest_app
from auth_service.auth_adapter.rest import router as auth_adapter_router_module
from auth_service.claims_repository.deps import get_claim_dao
from auth_service.config import CONFIG, Config
from auth_service.user_registry.deps import (
    get_iva_dao,
    get_user_dao,
    get_user_registry,
)

from ...fixtures.utils import (
    RE_USER_INFO_URL,
    USER_INFO,
    MockClaimDao,
    MockUserRegistry,
    MockUserTokenDao,
    create_access_token,
    headers_for_session,
)

AUTH_PATH = CONFIG.api_ext_path.strip("/")
if AUTH_PATH:
    AUTH_PATH = "/" + AUTH_PATH

totp_encryption_key = TOTPHandler.random_encryption_key()


@pytest_asyncio.fixture(name="bare_client")
async def fixture_bare_client(kafka: KafkaFixture) -> AsyncGenerator[BareClient]:
    """Get a test client for the auth adapter without database."""
    config = Config(
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        totp_encryption_key=SecretStr(totp_encryption_key),
    )  # type: ignore

    async with prepare_rest_app(config=config) as app, BareClient(app) as client:
        yield client


class ClientWithBasicAuth(NamedTuple):
    """A test client with basic auth."""

    bare_client: BareClient
    credentials: str


class ClientWithSession(NamedTuple):
    """A test client with a client session."""

    bare_client: BareClient
    session: Session
    user_registry: MockUserRegistry
    user_token_dao: MockUserTokenDao


_map_session_dict_to_object = {
    "ext_id": "ext_id",
    "id": "user_id",
    "name": "user_name",
    "email": "user_email",
    "title": "user_title",
    "roles": "roles",
    "csrf": "csrf_token",
}


def session_from_response(response: Response, session_id: str | None = None) -> Session:
    """Get a session object from the response."""
    if not session_id:
        session_id = response.cookies.get(SESSION_COOKIE)
        assert session_id
    session_header = response.headers.get("X-Session")
    assert session_header
    session_dict = json.loads(session_header)
    for key, attr in _map_session_dict_to_object.items():
        session_dict[attr] = session_dict.pop(key, None)
    now = now_as_utc()
    last_used = now - timedelta(seconds=session_dict.pop("timeout", 0))
    created = last_used - timedelta(seconds=session_dict.pop("extends", 0))
    session_dict.update(last_used=last_used, created=created)
    session = Session(session_id=session_id, **session_dict)
    assert session.totp_token is None  # should never be passed to the client
    return session


async def query_new_session(
    bare_client: BareClient, session: Session | None = None
) -> Session:
    """Query the current backend session."""
    if session:
        headers = headers_for_session(session)
    else:
        auth = f"Bearer {create_access_token()}"
        headers = {"Authorization": auth}
    response = await bare_client.post(f"{AUTH_PATH}/rpc/login", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert "X-CSRF-Token" not in response.headers
    session_id: str | None
    if session:
        assert SESSION_COOKIE not in response.cookies
        session_id = session.session_id
    else:
        session_id = response.cookies.get(SESSION_COOKIE)
    assert session_id
    session_header = response.headers.get("X-Session")
    assert session_header
    session_dict = json.loads(session_header)
    for key, attr in _map_session_dict_to_object.items():
        session_dict[attr] = session_dict.pop(key, None)
    now = now_as_utc()
    last_used = now - timedelta(seconds=session_dict.pop("timeout", 0))
    created = last_used - timedelta(seconds=session_dict.pop("extends", 0))
    session_dict.update(last_used=last_used, created=created)
    session = Session(session_id=session_id, **session_dict)
    assert session.totp_token is None  # should never be passed to the client
    return session


@pytest_asyncio.fixture(name="client_with_session")
async def fixture_bare_client_with_session(
    bare_client: BareClient, httpx_mock: HTTPXMock
) -> AsyncGenerator[ClientWithSession]:
    """Get test client for the auth adapter with a logged in user"""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)

    user_registry = MockUserRegistry()
    user_dao = user_registry.mock_user_dao
    iva_dao = user_registry.mock_iva_dao
    user_token_dao = MockUserTokenDao()
    claim_dao = MockClaimDao()

    overrides = bare_client.app.dependency_overrides
    overrides[get_user_dao] = lambda: user_dao
    overrides[get_iva_dao] = lambda: iva_dao
    overrides[get_user_registry] = lambda: user_registry
    overrides[get_user_token_dao] = lambda: user_token_dao
    overrides[get_claim_dao] = lambda: claim_dao

    session = await query_new_session(bare_client)

    yield ClientWithSession(bare_client, session, user_registry, user_token_dao)


@pytest_asyncio.fixture(name="client_with_basic_auth")
async def fixture_bare_client_with_basic_auth(
    kafka: KafkaFixture,
) -> AsyncGenerator[ClientWithBasicAuth]:
    """Get a test client for the user registry with Basic auth."""
    # create a config with Basic auth credentials
    credentials = "testuser:testpwd"
    config = Config(
        basic_auth_credentials=credentials,
        allow_read_paths=["/allowed/read/*", "/logo.png"],
        allow_write_paths=["/allowed/write/*"],
        kafka_servers=kafka.config.kafka_servers,
        service_name=kafka.config.service_name,
        service_instance_id=kafka.config.service_instance_id,
        totp_encryption_key=SecretStr(totp_encryption_key),
    )  # type: ignore

    # create app with the changed config
    config_module.CONFIG = config
    try:
        # reload to make the changes affect the router
        reload(auth_adapter_router_module)
        reload(auth_adapter_prepare_module)
        async with prepare_rest_app(config=config) as app, BareClient(app) as client:
            yield ClientWithBasicAuth(client, credentials)

    finally:
        config_module.CONFIG = CONFIG
        reload(auth_adapter_router_module)
        reload(auth_adapter_prepare_module)
