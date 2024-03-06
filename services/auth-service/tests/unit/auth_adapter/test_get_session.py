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

"""Test the dependency for geting the current session."""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from pytest import mark, raises

from auth_service.auth_adapter.adapters.memory_session_store import MemorySessionStore
from auth_service.auth_adapter.deps import get_session
from auth_service.config import CONFIG

pytestmark = mark.asyncio(scope="module")

SESSION_COOKIE = "session"
CSRF_TOKEN_HEADER = "X-CSRF-Token"

SESSION_ARGS = {
    "ext_id": "john@aai.org",
    "user_name": "John Doe",
    "user_email": "john@home.org",
}

UNCRITICAL_METHODS = ["GET", "HEAD", "OPTION"]
CRITICAL_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
ALL_METHODS = UNCRITICAL_METHODS + CRITICAL_METHODS

EXPECTED_ERROR_STATUS = status.HTTP_401_UNAUTHORIZED
EXPECTED_ERROR_MESSAGE = "Invalid or missing CSRF token"


async def assert_get_session(
    method: str = "GET",
    with_cookie: bool | str = True,
    with_csrf_token: bool | str = True,
    expect_result: bool | None = True,
) -> None:
    """Assert that the session is retrieved correctly.

    If `expect_result` is None, then the session should not be found.
    If it is False, then HTTPException with a CSRF error should be raised.
    """
    store = MemorySessionStore(config=CONFIG)

    session = await store.create_session(**SESSION_ARGS)

    if with_cookie is False:
        cookie = None
    elif with_cookie is True:
        cookie = session.session_id
    else:
        cookie = with_cookie

    if with_csrf_token is False:
        csrf_token = None
    elif with_csrf_token is True:
        csrf_token = session.csrf_token
    else:
        csrf_token = with_csrf_token

    headers: list[tuple[bytes, bytes]] = []
    if cookie is not None:
        headers.append((b"cookie", f"{SESSION_COOKIE}={cookie}".encode()))
    if csrf_token is not None:
        headers.append((CSRF_TOKEN_HEADER.lower().encode(), csrf_token.encode()))

    request = Request(
        {"type": "http", "method": method, "headers": headers, "path": "/some/path"}
    )
    if expect_result is False:
        with raises(HTTPException) as exc_info:
            await get_session(store, request)
        assert exc_info.value.status_code == EXPECTED_ERROR_STATUS
        assert exc_info.value.detail == EXPECTED_ERROR_MESSAGE
    else:
        returned_session = await get_session(store, request)
        expected_session = None if expect_result is None else session
        assert returned_session is expected_session


@mark.parametrize("method", ALL_METHODS)
async def test_get_session_without_cookie(method: str) -> None:
    """Test getting the session without a cookie."""
    await assert_get_session(method, with_cookie=False, expect_result=None)


@mark.parametrize("method", ALL_METHODS)
async def test_get_session_with_invalid_cookie(method: str) -> None:
    """Test getting the session wit an invalid cookie."""
    await assert_get_session(method, with_cookie="bad-cookie", expect_result=None)


@mark.parametrize("method", ALL_METHODS)
async def test_get_session_without_cookie_and_without_csrf_token(method: str) -> None:
    """Test getting the session without a cookie and without a CSRF token."""
    await assert_get_session(
        method, with_cookie=False, with_csrf_token=False, expect_result=None
    )


@mark.parametrize("method", ALL_METHODS)
async def test_get_session_without_cookie_and_invalid_csrf_token(method: str) -> None:
    """Test getting the session without a cookie and an invalid CSRF token."""
    await assert_get_session(
        method, with_cookie=False, with_csrf_token="bad-token", expect_result=None
    )


@mark.parametrize("method", UNCRITICAL_METHODS)
async def test_get_session_uncritical_without_csrf_token(method: str) -> None:
    """Test getting the session with an uncritical method and no CSRF token."""
    await assert_get_session(method, with_csrf_token=False)


@mark.parametrize("method", CRITICAL_METHODS)
async def test_get_session_critical_method_without_csrf_token(method: str) -> None:
    """Test CSRF protection with a critical method and no CSRF token."""
    await assert_get_session(method, with_csrf_token=False, expect_result=False)


@mark.parametrize("method", UNCRITICAL_METHODS)
async def test_get_session_on_uncritical_method_with_invalid_token(method: str) -> None:
    """Test CSRF protection with a critical method and invalid CSRF token."""
    await assert_get_session(method, with_csrf_token="bad-token")


@mark.parametrize("method", CRITICAL_METHODS)
async def test_get_session_on_critical_method_with_invalid_token(method: str) -> None:
    """Test CSRF protection with a critical method and invalid CSRF token."""
    await assert_get_session(method, with_csrf_token="bad-token", expect_result=False)


@mark.parametrize("method", UNCRITICAL_METHODS)
async def test_get_session_on_uncritical_method_with_valid_token(method: str) -> None:
    """Test CSRF protection with an uncritical method and valid CSRF token."""
    await assert_get_session(method)


@mark.parametrize("method", CRITICAL_METHODS)
async def test_get_session_on_critical_method_with_valid_token(method: str) -> None:
    """Test CSRF protection with a critical method and a valid CSRF token."""
    await assert_get_session(method)
