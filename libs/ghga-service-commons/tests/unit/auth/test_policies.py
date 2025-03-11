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
#

"""Test the auth.policies module."""

from __future__ import annotations

import pytest
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.policies import (
    get_auth_context_using_credentials,
    require_auth_context_using_credentials,
)


class DummyAuthContext(BaseModel):
    """Dummy auth context for testing."""

    token: str


class DummyAuthProvider(AuthContextProtocol[DummyAuthContext]):
    """Dummy auth provider for testing."""

    async def get_context(self, token: str) -> DummyAuthContext | None:
        """Return a dummy auth context."""
        if not token:
            return None
        if "invalid" in token:
            raise self.AuthContextValidationError
        return DummyAuthContext(token=token)


def dummy_predicate(context: DummyAuthContext) -> bool:
    """Return a dummy auth context predicate for testing."""
    return context.token == "super"


pytestmark = pytest.mark.asyncio


async def test_get_auth_context_no_token():
    """Test passing no token to the get_auth_context function."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
    auth_provider = DummyAuthProvider()
    context = await get_auth_context_using_credentials(credentials, auth_provider)
    assert context is None


async def test_get_auth_context_invalid_token():
    """Test passing an invalid token to the get_auth_context function."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
    auth_provider = DummyAuthProvider()
    with pytest.raises(HTTPException) as exc_info:
        await get_auth_context_using_credentials(credentials, auth_provider)
    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid authentication credentials"


async def test_get_auth_context_with_valid_token():
    """Test passing a valid token to the get_auth_context function."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid")
    auth_provider = DummyAuthProvider()
    context = await get_auth_context_using_credentials(credentials, auth_provider)
    assert context is not None
    assert context.token == "valid"


async def test_require_auth_context_no_token():
    """Test passing no token to the require_auth_context function."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
    auth_provider = DummyAuthProvider()
    with pytest.raises(HTTPException) as exc_info:
        await require_auth_context_using_credentials(credentials, auth_provider)
    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Not authenticated"


async def test_require_auth_context_invalid_token():
    """Test passing an invalid token to the require_auth_context function."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
    auth_provider = DummyAuthProvider()
    with pytest.raises(HTTPException) as exc_info:
        await require_auth_context_using_credentials(credentials, auth_provider)
    assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid authentication credentials"


async def test_require_auth_context_with_valid_token():
    """Test passing a valid token to the require_auth_context function."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid")
    auth_provider = DummyAuthProvider()
    context = await require_auth_context_using_credentials(credentials, auth_provider)
    assert context is not None
    assert context.token == "valid"


async def test_require_auth_context_with_happy_predicate():
    """Test the happy path of the require_auth_context function with a predicate."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="super")
    auth_provider = DummyAuthProvider()
    context = await require_auth_context_using_credentials(
        credentials, auth_provider, dummy_predicate
    )
    assert context is not None
    assert context.token == "super"


async def test_require_auth_context_with_unhappy_predicate():
    """Test the unhappy path of the require_auth_context function with a predicate."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="normal")
    auth_provider = DummyAuthProvider()
    with pytest.raises(HTTPException) as exc_info:
        await require_auth_context_using_credentials(
            credentials, auth_provider, dummy_predicate
        )
    assert exc_info.value.status_code == HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Not authorized"
