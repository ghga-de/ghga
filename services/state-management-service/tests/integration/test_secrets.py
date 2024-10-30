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
"""Integration tests for the /secrets endpoints."""

from typing import Any

import pytest
from ghga_service_commons.api.testing import AsyncTestClient

from sms.inject import prepare_rest_app
from tests.fixtures.config import get_config
from tests.fixtures.utils import VALID_BEARER_TOKEN
from tests.fixtures.vault import (  # noqa: F401
    DEFAULT_VAULT_PATH,
    VaultFixture,
    vault_container_fixture,
    vault_fixture,
)

TEST_URL = f"/secrets/{DEFAULT_VAULT_PATH}"
pytestmark = pytest.mark.asyncio()
HEADERS: dict[str, Any] = {"Authorization": VALID_BEARER_TOKEN}


@pytest.mark.parametrize(
    "stored_secrets",
    [[], ["key1"], ["key1", "key2"]],
    ids=["empty", "single", "multiple"],
)
async def test_happy_get(vault: VaultFixture, stored_secrets: list[str]):
    """Test that the GET /secrets endpoint returns the correct response."""
    vault_fixture_config = vault.config
    config = get_config(sources=[vault_fixture_config])

    for secret in stored_secrets:
        vault.store_secret(key=secret)

    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.get(TEST_URL, headers=HEADERS)
        assert response.status_code == 200
        assert set(response.json()) == set(stored_secrets)


@pytest.mark.parametrize(
    "stored_secrets",
    [[], ["key1"], ["key1", "key2"]],
    ids=["Empty", "OneKey", "TwoKeys"],
)
async def test_happy_delete(vault: VaultFixture, stored_secrets: list[str]):
    """Test that the DELETE /secrets endpoint returns the correct response."""
    vault_fixture_config = vault.config
    config = get_config(sources=[vault_fixture_config])

    # Store the secrets in the vault
    for secret in stored_secrets:
        vault.store_secret(key=secret)

    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        # Make a DELETE request to delete the secrets
        response = await client.delete(TEST_URL, headers=HEADERS)
        assert response.status_code == 204

        # Make a GET request to check if the secrets were deleted
        response = await client.get(TEST_URL, headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == []


async def test_nonexistent_vault_path(vault: VaultFixture):
    """Ensure both endpoint return the right response when `vault_path` doesn't exist."""
    vault_fixture_config = vault.config
    config = get_config(sources=[vault_fixture_config])

    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.get("/secrets/doesnotexist", headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == []

        response = await client.delete("/secrets/doesnotexist", headers=HEADERS)
        assert response.status_code == 204
