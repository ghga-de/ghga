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

"""Test the REST API."""

import asyncio

from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest import fixture

from ghga_auth.config import AUTH_KEY_PAIR, Config
from ghga_auth.main import get_configured_app, get_configured_container
from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token


async def get_app() -> FastAPI:
    """Get the demo app."""
    config = Config()  # pyright: ignore
    async with get_configured_container(config) as container:
        container.wire(modules=["ghga_auth.policies"])
        return get_configured_app(config)


@fixture
def client() -> TestClient:
    """Get test client for the demo app."""
    return TestClient(asyncio.run(get_app()))


def get_headers(active: bool = False, admin: bool = False) -> dict[str, str]:
    """Get a request header with an auth token for testing."""
    claims = {
        "name": "John Doe",
        "email": "john@home.org",
        "title": "Dr.",
        "id": "john-doe@ghga",
        "ext_id": "john-doe@home",
    }
    if active:
        claims["status"] = "active"
    if admin:
        claims["role"] = "admin"
    token = sign_and_serialize_token(claims, AUTH_KEY_PAIR)
    return {"Authorization": f"Bearer {token}"}


def test_get_auth_unauthenticated(client):
    """Test the get_auth endpoint unauthenticated."""
    response = client.get("/get_auth")
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert isinstance(res, dict)
    assert res["context"] is None


def test_get_auth_authenticated(client):
    """Test the get_auth endpoint authenticated."""
    response = client.get("/get_auth", headers=get_headers())
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
        "ext_id": "john-doe@home",
        "role": None,
        "status": None,
    }


def test_require_auth_unauthenticated(client):
    """Test the require_auth endpoint unauthenticated."""
    response = client.get("/require_auth")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}


def test_require_auth_authenticated(client):
    """Test the require_auth endpoint authenticated."""
    response = client.get("/require_auth", headers=get_headers())
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
        "ext_id": "john-doe@home",
        "role": None,
        "status": None,
    }


def test_require_active_unauthenticated(client):
    """Test the require_active endpoint unauthenticated."""
    response = client.get("/require_active")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}


def test_require_active_authenticated_but_inactive(client):
    """Test the require_auth endpoint authenticated but inactive."""
    response = client.get("/require_active", headers=get_headers())
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authorized"}


def test_require_active_authenticated_and_active(client):
    """Test the require_auth endpoint authenticated and active."""
    response = client.get("/require_auth", headers=get_headers(active=True))
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
        "ext_id": "john-doe@home",
        "role": None,
        "status": "active",
    }


def test_require_admin_unauthenticated(client):
    """Test the require_admin endpoint unauthenticated."""
    response = client.get("/require_admin")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}


def test_require_admin_authenticated_but_not_admin(client):
    """Test the require_admin endpoint authenticated, but not as admin."""
    response = client.get("/require_admin", headers=get_headers())
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authorized"}


def test_require_admin_authenticated_as_inactive_admin(client):
    """Test the require_admin endpoint authenticated, but as inactive admin."""
    response = client.get("/require_admin", headers=get_headers(admin=True))
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authorized"}


def test_require_admin_authenticated_as_active_admin(client):
    """Test the require_admin endpoint authenticated as admin."""
    response = client.get(
        "/require_admin", headers=get_headers(active=True, admin=True)
    )
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
        "ext_id": "john-doe@home",
        "role": "admin",
        "status": "active",
    }
