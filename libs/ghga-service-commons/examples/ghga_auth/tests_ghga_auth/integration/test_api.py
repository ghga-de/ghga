# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the REST API."""

import asyncio
from typing import Any

import pytest
from fastapi import status
from ghga_auth.config import AUTH_KEY_PAIR, Config
from ghga_auth.inject import prepare_rest_app

from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token


async def get_app():
    """Get the demo app."""
    config = Config()  # pyright: ignore

    async with prepare_rest_app(config=config) as app:
        return app


@pytest.fixture
def client() -> AsyncTestClient:
    """Get test client for the demo app."""
    return AsyncTestClient(asyncio.run(get_app()))


def get_headers(admin: bool = False) -> dict[str, str]:
    """Get a request header with an auth token for testing."""
    claims: dict[str, Any] = {
        "name": "John Doe",
        "email": "john@home.org",
        "title": "Dr.",
        "id": "john-doe@ghga",
    }
    if admin:
        claims["roles"] = ["admin"]
    token = sign_and_serialize_token(claims, AUTH_KEY_PAIR)
    return {"Authorization": f"Bearer {token}"}


pytestmark = pytest.mark.asyncio


async def test_get_auth_unauthenticated(client):
    """Test the get_auth endpoint unauthenticated."""
    response = await client.get("/get_auth")
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert isinstance(res, dict)
    assert res["context"] is None


async def test_get_auth_authenticated(client):
    """Test the get_auth endpoint authenticated."""
    response = await client.get("/get_auth", headers=get_headers())
    assert response.status_code == status.HTTP_200_OK
    res = response.json()
    assert isinstance(res, dict)
    context = res["context"]
    assert isinstance(context, dict)
    assert context.pop("iat")
    assert context.pop("exp")
    assert context == {
        "name": "John Doe",
        "email": "john@home.org",
        "title": "Dr.",
        "id": "john-doe@ghga",
        "roles": [],
    }


async def test_require_auth_unauthenticated(client):
    """Test the require_auth endpoint unauthenticated."""
    response = await client.get("/require_auth")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


async def test_require_auth_authenticated(client):
    """Test the require_auth endpoint authenticated."""
    response = await client.get("/require_auth", headers=get_headers())
    assert response.status_code == status.HTTP_200_OK
    res = response.json()
    assert isinstance(res, dict)
    context = res["context"]
    assert isinstance(context, dict)
    assert context.pop("iat")
    assert context.pop("exp")
    assert context == {
        "name": "John Doe",
        "email": "john@home.org",
        "title": "Dr.",
        "id": "john-doe@ghga",
        "roles": [],
    }


async def test_require_admin_unauthenticated(client):
    """Test the require_admin endpoint unauthenticated."""
    response = await client.get("/require_admin")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


async def test_require_admin_authenticated_but_not_admin(client):
    """Test the require_admin endpoint authenticated, but not as admin."""
    response = await client.get("/require_admin", headers=get_headers())
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authorized"}


async def test_require_admin_authenticated_as_admin(client):
    """Test the require_admin endpoint authenticated as admin."""
    response = await client.get("/require_admin", headers=get_headers(admin=True))
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert isinstance(res, dict)
    context = res["context"]
    assert isinstance(context, dict)
    assert context.pop("iat")
    assert context.pop("exp")
    assert context == {
        "name": "John Doe",
        "email": "john@home.org",
        "title": "Dr.",
        "id": "john-doe@ghga",
        "roles": ["admin"],
    }
