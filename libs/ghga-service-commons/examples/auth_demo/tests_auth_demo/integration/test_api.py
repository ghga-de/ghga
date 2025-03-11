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

"""Test the REST API."""

import asyncio

import pytest
from fastapi import FastAPI, status

from auth_demo.config import Config
from auth_demo.inject import prepare_rest_app
from ghga_service_commons.api.testing import AsyncTestClient

pytestmark = pytest.mark.asyncio


async def get_app() -> FastAPI:
    """Get the demo app."""
    config = Config()
    async with prepare_rest_app(config=config) as app:
        return app


@pytest.fixture
def client() -> AsyncTestClient:
    """Get test client for the demo app."""
    return AsyncTestClient(asyncio.run(get_app()))


def get_token(users: list[dict], name: str) -> str:
    """Get specific user token from a list of users."""
    assert isinstance(users, list)
    users = [user for user in users if user.get("name", "").startswith(name)]
    assert len(users) == 1
    user = users[0]
    assert "token" in user
    assert "is_vip" in user
    token = user["token"]
    assert len(token) > 80
    assert token.count(".") == 2
    chars = token.replace(".", "").replace("-", "").replace("_", "")
    assert chars.isalnum()
    assert chars.isascii()
    return token


async def test_index(client):
    """Test the index endpoint."""
    response = await client.get("/")
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert isinstance(res, dict)
    assert res["message"] == "Hello, world!"
    assert "reception" in res["endpoints"]


async def test_users(client):
    """Test the users endpoint."""
    response = await client.get("/users")
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert isinstance(res, dict)
    users = res["users"]
    assert len(users) == 4
    assert get_token(users, "Ada")


async def test_status(client):
    """Test the status endpoint."""
    response = await client.get("/status")
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert res == {"status": "logged out"}

    response = await client.get("/users")
    token = get_token(response.json()["users"], "Grace")

    response = await client.get("/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert res["status"].startswith("logged in until")


async def test_reception(client):
    """Test the reception endpoint."""
    response = await client.get("/reception")
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert res == {"message": "Hello, anonymous user!"}

    response = await client.get("/users")
    token = get_token(response.json()["users"], "Grace")

    response = await client.get(
        "/reception", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert res == {"message": "Hello, Grace Hopper!"}


async def test_lobby(client):
    """Test the lobby endpoint."""
    response = await client.get("/lobby")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}

    response = await client.get("/users")
    token = get_token(response.json()["users"], "Ada")

    response = await client.get("/lobby", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert res == {"message": "Hello, Ada Lovelace!"}


async def test_lounge(client):
    """Test the lounge endpoint."""
    response = await client.get("/lounge")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authenticated"}

    response = await client.get("/users")
    token_ada = get_token(response.json()["users"], "Ada")
    token_grace = get_token(response.json()["users"], "Alan")

    response = await client.get(
        "/lounge", headers={"Authorization": f"Bearer {token_ada}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Not authorized"}

    response = await client.get(
        "/lounge", headers={"Authorization": f"Bearer {token_grace}"}
    )
    assert response.status_code == status.HTTP_200_OK

    res = response.json()
    assert res == {"message": "Hello, dear Alan Turing, have a beer!"}
