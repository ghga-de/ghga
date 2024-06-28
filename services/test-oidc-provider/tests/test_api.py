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

"""Tests for the REST API"""

from collections.abc import AsyncGenerator

from fastapi import status
from ghga_service_commons.api.testing import AsyncTestClient
from pytest import mark
from pytest_asyncio import fixture as async_fixture

from top import __version__
from top.api.main import app, oidc_provider


@async_fixture(name="client")
async def fixture_client() -> AsyncGenerator[AsyncTestClient, None]:
    """Get test client for this application."""
    async with AsyncTestClient(app=app) as client:
        yield client


def headers_for_token(token: str) -> dict[str, str]:
    """Get the Authorization headers for the given token."""
    return {"Authorization": f"Bearer {token}"}


@mark.asyncio
async def test_health_check(client: AsyncTestClient):
    """Test that the health check endpoint works."""
    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


@mark.parametrize("origin_header", [None, "x-forwarded", "x-envoy-original"])
@mark.asyncio
async def test_openid_configuration(origin_header: str | None, client: AsyncTestClient):
    """Test getting the OpenID configuration from the well-known path."""
    if origin_header:
        scheme = "https"
        host = "some-hostname.dev"
        path = "/some-path/.well-known/openid-configuration"
        headers = {
            f"{origin_header}-proto": scheme,
            f"{origin_header}-host": host,
            f"{origin_header}-path": path,
        }
        base_url = "https://some-hostname.dev/some-path"
    else:
        headers = None
        base_url = "http://localhost:8080"

    response = await client.get("/.well-known/openid-configuration", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    openid_config = response.json()
    assert openid_config == {
        "version": __version__,
        "issuer": "https://op.test",
        "jwks_uri": f"{base_url}/jwks",
        "scopes_supported": ["openid", "profile", "email"],
        "claims_supported": ["sub", "name", "email"],
        "request_object_signing_alg_values_supported": ["ES512"],
        "userinfo_signing_alg_values_supported": ["ES512"],
        "userinfo_endpoint": f"{base_url}/userinfo",
        "service_documentation": "https://github.com/ghga-de/test-oidc-provider",
    }


@mark.asyncio
async def test_jwks_via_uri(client: AsyncTestClient):
    """Test getting the JWKS via the well-known path."""
    response = await client.get("/.well-known/openid-configuration")

    openid_config = response.json()
    assert isinstance(openid_config, dict)
    jwks_uri = openid_config["jwks_uri"]
    assert jwks_uri == "http://localhost:8080/jwks"

    response = await client.get(jwks_uri)
    assert response.status_code == status.HTTP_200_OK

    jwks = response.json()
    assert isinstance(jwks, dict)
    assert list(jwks) == ["keys"]
    keys = jwks["keys"]
    assert isinstance(keys, list)
    assert all("use" in key and "kty" in key and "kid" in key for key in keys)


@mark.asyncio
async def test_get_user_info_without_login(client: AsyncTestClient):
    """Test getting user info without first logging in."""
    response = await client.get("/userinfo")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = await client.get("/userinfo", headers=headers_for_token("foo.bar.baz"))
    assert response.status_code == status.HTTP_403_FORBIDDEN


@mark.asyncio
async def test_login_and_get_user_info(client: AsyncTestClient):
    """Test logging in as a user and getting the user info back."""
    response = await client.post("/login", json={"name": "John Doe"})
    assert response.status_code == status.HTTP_201_CREATED

    token = response.text
    assert token and token.isascii() and token.count(".") == 2
    claims = oidc_provider.decode_and_validate_token(token)
    iat, exp = claims.pop("iat"), claims.pop("exp")
    assert isinstance(iat, int)
    assert isinstance(exp, int)
    assert exp - iat == 60 * 60
    assert claims == {
        "aud": ["test-client"],
        "client_id": "test-client",
        "iss": "https://op.test",
        "jti": "test-1",
        "scope": "openid profile email",
        "sid": "test-1",
        "sub": "id-of-john-doe@op.test",
        "token_class": "access_token",
    }

    response = await client.get("/userinfo")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = await client.get("/userinfo", headers=headers_for_token(token))
    assert response.status_code == status.HTTP_200_OK

    user_info = response.json()
    assert user_info == {
        "email": "john.doe@home.org",
        "name": "John Doe",
        "sub": "id-of-john-doe@op.test",
    }
