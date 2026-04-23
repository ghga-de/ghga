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

"""Unit tests for the secrets client."""

from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from pydantic import HttpUrl, SecretBytes
from pytest_httpx import HTTPXMock

from fis.adapters.outbound.http import HttpClientConfig, get_configured_httpx_client
from fis.adapters.outbound.secrets import SecretsClient, SecretsClientConfig

pytestmark = pytest.mark.asyncio

BASE_URL = "http://ekss.test"
SECRET_ID = "test-secret-id-12345"
SECRET_BYTES = SecretBytes(b"encrypted-secret-data")
HTTP_CONFIG = HttpClientConfig(client_num_retries=0)
SECRETS_CONFIG = SecretsClientConfig(ekss_api_url=HttpUrl(BASE_URL))


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[SecretsClient]:
    """Construct a SecretsClient backed by the configured httpx client."""
    async with get_configured_httpx_client(config=HTTP_CONFIG) as httpx_client:
        yield SecretsClient(config=SECRETS_CONFIG, httpx_client=httpx_client)


async def test_happy_deposition(httpx_mock: HTTPXMock, client: SecretsClient):
    """Test that a secret is sent to the right URL and that a str is returned"""
    httpx_mock.add_response(
        url=f"{BASE_URL}/secrets",
        method="POST",
        status_code=201,
        json={"secret_id": SECRET_ID},
    )

    result = await client.deposit_secret(secret=SECRET_BYTES)

    assert result == SECRET_ID
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert str(request.url) == f"{BASE_URL}/secrets"


async def test_deposition_errors(httpx_mock: HTTPXMock, client: SecretsClient):
    """Test the various error handling when depositing secrets"""
    # Non-201 status code should raise SecretsApiError
    httpx_mock.add_response(
        url=f"{BASE_URL}/secrets",
        method="POST",
        status_code=500,
    )

    with pytest.raises(SecretsClient.SecretsApiError):
        await client.deposit_secret(secret=SECRET_BYTES)

    # Network-level error should also raise SecretsApiError
    httpx_mock.add_exception(
        httpx.ConnectError("Connection refused"),
        url=f"{BASE_URL}/secrets",
        method="POST",
    )

    with pytest.raises(SecretsClient.SecretsApiError):
        await client.deposit_secret(secret=SECRET_BYTES)

    # Invalid JSON response body should raise SecretsApiError
    httpx_mock.add_response(
        url=f"{BASE_URL}/secrets",
        method="POST",
        status_code=201,
        content=b"not valid json",
    )

    with pytest.raises(SecretsClient.SecretsApiError):
        await client.deposit_secret(secret=SECRET_BYTES)


async def test_happy_deletion(httpx_mock: HTTPXMock, client: SecretsClient):
    """Test that a secret ID is sent to the right URL/HTTP method"""
    # 204 No Content is the normal success response
    httpx_mock.add_response(
        url=f"{BASE_URL}/secrets/{SECRET_ID}",
        method="DELETE",
        status_code=204,
    )

    await client.delete_secret(secret_id=SECRET_ID)

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "DELETE"
    assert str(request.url) == f"{BASE_URL}/secrets/{SECRET_ID}"

    # 404 should also be treated as success (already gone)
    httpx_mock.add_response(
        url=f"{BASE_URL}/secrets/{SECRET_ID}",
        method="DELETE",
        status_code=404,
    )

    await client.delete_secret(secret_id=SECRET_ID)  # should not raise


async def test_deletion_errors(httpx_mock: HTTPXMock, client: SecretsClient):
    """Test the various error handling when deleting secrets"""
    # Non-204/404 status code should raise SecretsApiError
    httpx_mock.add_response(
        url=f"{BASE_URL}/secrets/{SECRET_ID}",
        method="DELETE",
        status_code=500,
    )

    with pytest.raises(SecretsClient.SecretsApiError):
        await client.delete_secret(secret_id=SECRET_ID)

    # Network-level error should also raise SecretsApiError
    httpx_mock.add_exception(
        httpx.ConnectError("Connection refused"),
        url=f"{BASE_URL}/secrets/{SECRET_ID}",
        method="DELETE",
    )

    with pytest.raises(SecretsClient.SecretsApiError):
        await client.delete_secret(secret_id=SECRET_ID)
