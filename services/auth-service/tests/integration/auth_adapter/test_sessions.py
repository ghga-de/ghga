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
#

"""Test handling user sessions in the auth adapter."""

import json
from typing import Union

from fastapi import status
from ghga_service_commons.api.testing import AsyncTestClient
from httpx import Response
from pytest import mark
from pytest_httpx import HTTPXMock

from auth_service.auth_adapter.api import main
from auth_service.auth_adapter.deps import get_session_store
from auth_service.config import CONFIG
from auth_service.user_management.user_registry.deps import get_user_dao

from ...fixtures.utils import (
    RE_USER_INFO_URL,
    USER_INFO,
    DummyUserDao,
    create_access_token,
    headers_for_session,
)
from .fixtures import fixture_client  # noqa: F401


def expected_set_cookie(session_id: str) -> str:
    """Get the expected Set-Cookie header for the auth session cookie."""
    return f"session={session_id}; HttpOnly; Path=/; SameSite=lax; Secure"


def assert_session_header(
    response: Response, expected: dict[str, Union[str, int]]
) -> None:
    """Assert that the response session header is as expected."""
    session_header = response.headers.get("X-Session")
    assert session_header
    session = json.loads(session_header)
    assert isinstance(session, dict)
    csrf_token = session.pop("csrf", None)
    assert len(csrf_token) == 32
    assert csrf_token.replace("-", "").replace("_", "").isalnum()
    timeout = session.pop("timeout", None)
    assert isinstance(timeout, int)
    assert timeout == 60 * 60
    extends = session.pop("extends", None)
    assert isinstance(extends, int)
    assert extends == 12 * 60 * 60
    assert session == expected


@mark.asyncio
async def test_logout(client: AsyncTestClient):
    """Test that a logout request removes the user session."""
    store = await get_session_store(config=CONFIG)
    session = await store.create_session(
        user_id="john@ghga.de", user_name="John Doe", user_email="john@home.org"
    )
    assert await store.get_session(session.session_id)
    headers = headers_for_session(session)
    response = await client.post("/rpc/logout", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not await store.get_session(session.session_id)

    assert "session" not in response.cookies
    assert "X-Session" not in response.headers


@mark.asyncio
async def test_logout_without_session(client: AsyncTestClient):
    """Test that a logout request without a session does not fail."""
    response = await client.post("/rpc/logout")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert "session" not in response.cookies
    assert "X-Session" not in response.headers


@mark.asyncio
async def test_logout_with_invalid_csrf_token(client: AsyncTestClient):
    """Test that a logout request with an invalid CSRF token fails."""
    store = await get_session_store(config=CONFIG)
    session = await store.create_session(
        user_id="john@ghga.de", user_name="John Doe", user_email="john@home.org"
    )
    original_session = session.model_copy()
    headers = headers_for_session(session)
    headers["X-CSRF-Token"] += "-invalidated"
    assert await store.get_session(session.session_id)
    response = await client.post("/rpc/logout", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "X-CSRF-Token" not in response.headers
    assert response.json() == {"detail": "Invalid or missing CSRF token"}
    assert await store.get_session(session.session_id) == original_session

    assert "session" not in response.cookies
    assert "X-Session" not in response.headers


@mark.asyncio
async def test_login_with_unregistered_user(
    client: AsyncTestClient, httpx_mock: HTTPXMock
):
    """Test that a login request can create a new session for an unregistered user."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)

    user_dao = DummyUserDao(ext_id="not.john@aai.org")
    main.app.dependency_overrides[get_user_dao] = lambda: user_dao

    auth = f"Bearer {create_access_token()}"
    response = await client.post("/rpc/login", headers={"Authorization": auth})
    assert response.status_code == status.HTTP_204_NO_CONTENT
    session_id = response.cookies.get("session")
    assert session_id
    store = await get_session_store(config=CONFIG)
    session_dict = await store.get_session(session_id)
    assert session_dict
    assert response.cookies.get("session") == session_id
    assert response.headers.get("set-cookie") == expected_set_cookie(session_id)
    assert_session_header(
        response,
        {
            "userId": "john@aai.org",
            "name": "John Doe",
            "email": "john@home.org",
            "state": "NeedsRegistration",
        },
    )


@mark.asyncio
async def test_login_with_invalid_userinfo(
    client: AsyncTestClient, httpx_mock: HTTPXMock
):
    """Test that a login request fails when user info cannot be retrieved."""
    bad_user_info = {**USER_INFO, "sub": "not.john@aai.org"}
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=bad_user_info)

    user_dao = DummyUserDao(ext_id="not.john@aai.org")
    main.app.dependency_overrides[get_user_dao] = lambda: user_dao

    auth = f"Bearer {create_access_token()}"
    response = await client.post("/rpc/login", headers={"Authorization": auth})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Subject in userinfo differs from access token"
    }

    assert "session" not in response.cookies
    assert "X-Session" not in response.headers


@mark.asyncio
async def test_login_with_registered_user(
    client: AsyncTestClient, httpx_mock: HTTPXMock
):
    """Test that a login request can create a new session for a registered user."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)

    user_dao = DummyUserDao(ext_id="john@aai.org")
    main.app.dependency_overrides[get_user_dao] = lambda: user_dao

    auth = f"Bearer {create_access_token()}"
    response = await client.post("/rpc/login", headers={"Authorization": auth})
    assert response.status_code == status.HTTP_204_NO_CONTENT
    session_id = response.cookies.get("session")
    assert session_id
    store = await get_session_store(config=CONFIG)
    session_dict = await store.get_session(session_id)
    assert session_dict
    assert response.cookies.get("session") == session_id
    assert response.headers.get("set-cookie") == expected_set_cookie(session_id)
    assert_session_header(
        response,
        {
            "userId": "john@ghga.de",
            "name": "John Doe",
            "email": "john@home.org",
            "state": "Registered",
        },
    )


@mark.asyncio
async def test_login_with_registered_user_and_name_change(
    client: AsyncTestClient, httpx_mock: HTTPXMock
):
    """Test a login request for a user when the name was changed."""
    changed_user_info = {**USER_INFO, "name": "John Doe Jr."}
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=changed_user_info)

    user_dao = DummyUserDao(ext_id="john@aai.org")
    main.app.dependency_overrides[get_user_dao] = lambda: user_dao

    auth = f"Bearer {create_access_token()}"
    response = await client.post("/rpc/login", headers={"Authorization": auth})
    assert response.status_code == status.HTTP_204_NO_CONTENT
    session_id = response.cookies.get("session")
    assert session_id
    store = await get_session_store(config=CONFIG)
    session_dict = await store.get_session(session_id)
    assert session_dict
    assert response.cookies.get("session") == session_id
    assert response.headers.get("set-cookie") == expected_set_cookie(session_id)
    assert_session_header(
        response,
        {
            "userId": "john@ghga.de",
            "name": "John Doe Jr.",
            "email": "john@home.org",
            "state": "NeedsReRegistration",
        },
    )


@mark.asyncio
async def test_login_with_registered_user_with_title(
    client: AsyncTestClient, httpx_mock: HTTPXMock
):
    """Test a login request for a user when a title was entered."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)

    user_dao = DummyUserDao(ext_id="john@aai.org", title="Dr.")
    main.app.dependency_overrides[get_user_dao] = lambda: user_dao

    auth = f"Bearer {create_access_token()}"
    response = await client.post("/rpc/login", headers={"Authorization": auth})
    assert response.status_code == status.HTTP_204_NO_CONTENT
    session_id = response.cookies.get("session")
    assert session_id
    store = await get_session_store(config=CONFIG)
    session_dict = await store.get_session(session_id)
    assert session_dict
    assert response.cookies.get("session") == session_id
    assert response.headers.get("set-cookie") == expected_set_cookie(session_id)
    assert_session_header(
        response,
        {
            "userId": "john@ghga.de",
            "name": "John Doe",
            "email": "john@home.org",
            "title": "Dr.",
            "state": "Registered",
        },
    )


@mark.asyncio
async def test_login_without_access_token(client: AsyncTestClient):
    """Test that a login request without an access token fails."""
    response = await client.post("/rpc/login")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "No access token provided"}

    assert "session" not in response.cookies
    assert "X-Session" not in response.headers


@mark.asyncio
async def test_login_with_invalid_access_token(client: AsyncTestClient):
    """Test that a login request with an invalid access token fails."""
    auth = "Bearer invalid"
    response = await client.post("/rpc/login", headers={"Authorization": auth})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Access token error: Not a valid token: Token format unrecognized"
    }

    assert "session" not in response.cookies
    assert "X-Session" not in response.headers


@mark.asyncio
async def test_login_with_cookie_and_unregistered_user(client: AsyncTestClient):
    """Test login request with session cookie for an unregistered user."""
    user_dao = DummyUserDao(ext_id="not.john@aai.org")
    main.app.dependency_overrides[get_user_dao] = lambda: user_dao

    store = await get_session_store(config=CONFIG)
    session = await store.create_session(
        user_id="john@aai.org", user_name="John Doe", user_email="john@home.org"
    )
    assert await store.get_session(session.session_id)
    headers = headers_for_session(session)
    response = await client.post("/rpc/login", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert "session" not in response.cookies
    assert_session_header(
        response,
        {
            "userId": "john@aai.org",
            "name": "John Doe",
            "email": "john@home.org",
            "state": "NeedsRegistration",
        },
    )


@mark.asyncio
async def test_login_with_cookie_and_registered_user(client: AsyncTestClient):
    """Test login request with session cookie for a registered user."""
    user_dao = DummyUserDao(ext_id="john@aai.org")
    main.app.dependency_overrides[get_user_dao] = lambda: user_dao

    store = await get_session_store(config=CONFIG)
    session_dict = await store.create_session(
        user_id="john@aai.org", user_name="John Doe", user_email="john@home.org"
    )
    assert await store.get_session(session_dict.session_id)
    headers = headers_for_session(session_dict)
    response = await client.post("/rpc/login", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert "session" not in response.cookies
    assert_session_header(
        response,
        {
            "userId": "john@ghga.de",
            "name": "John Doe",
            "email": "john@home.org",
            "state": "Registered",
        },
    )


@mark.asyncio
async def test_login_with_cookie_and_invalid_csrf_token(client: AsyncTestClient):
    """Test login request with session cookie and invalid CSRF token."""
    store = await get_session_store(config=CONFIG)
    session = await store.create_session(
        user_id="john@ghga.de", user_name="John Doe", user_email="john@home.org"
    )
    original_session = session.model_copy()
    assert await store.get_session(session.session_id)
    headers = headers_for_session(session)
    headers["X-CSRF-Token"] += "-invalidated"
    response = await client.post("/rpc/login", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "X-CSRF-Token" not in response.headers
    assert response.json() == {"detail": "Invalid or missing CSRF token"}

    assert await store.get_session(session.session_id) == original_session

    assert "session" not in response.cookies
    assert "X-Session" not in response.headers
