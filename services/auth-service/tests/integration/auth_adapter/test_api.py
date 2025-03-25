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

"""Test the api module"""

import logging
import re
from base64 import b64encode
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import status
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.correlation import validate_correlation_id
from pytest_httpx import HTTPXMock

from auth_service.auth_adapter.core.session_store import SessionState
from auth_service.auth_adapter.deps import get_user_token_dao
from auth_service.auth_adapter.rest.headers import get_bearer_token
from auth_service.user_management.claims_repository.deps import get_claim_dao
from auth_service.user_management.user_registry.deps import get_user_dao

from ...fixtures.utils import (
    DummyClaimDao,
    DummyUserDao,
    DummyUserTokenDao,
    get_claims_from_token,
    headers_for_session,
)
from .fixtures import (
    AUTH_PATH,
    BareClient,
    ClientWithBasicAuth,
    ClientWithSession,
    fixture_bare_client,  # noqa: F401
    fixture_bare_client_with_basic_auth,  # noqa: F401
    fixture_bare_client_with_session,  # noqa: F401
    query_new_session,
)
from .test_totp import get_valid_totp_code

pytestmark = pytest.mark.asyncio()

USER_INFO = {
    "name": "John Doe",
    "email": "john@home.org",
    "sub": "john@aai.org",
}
RE_USER_INFO_URL = re.compile(".*/userinfo$")


@pytest.fixture
def non_mocked_hosts() -> list:
    """Do not mock requests to the test server."""
    return ["testserver"]


def assert_has_authorization_header(response, session):
    """Check that the response contains the expected authorization header.

    Also test that the correlation ID is available in a response header.
    Though this is a feature provided by the service commons, we want to
    make sure that it works, since authorized requests are passed to the
    backend, and we want to be able to track them from ingress on.
    """
    assert response.status_code == status.HTTP_200_OK

    assert not response.text
    headers = response.headers
    assert not headers.get("Cookie")
    assert not headers.get("X-Authorization")
    assert not headers.get("X-CSRF-Token")
    assert not headers.get("X-Session")

    correlation_id = headers.get("X-Request-Id")
    assert correlation_id
    validate_correlation_id(correlation_id)

    authorization = headers.get("Authorization")
    assert authorization
    internal_token = get_bearer_token(authorization)
    assert internal_token
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"id", "name", "email", "title", "roles", "exp", "iat"}

    assert set(claims) == expected_claims
    assert claims["id"] == session.user_id
    assert claims["name"] == session.user_name
    assert claims["email"] == session.user_email
    assert claims["title"] == session.user_title
    assert claims["roles"] == session.roles
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]
    assert 0 <= claims["exp"] - claims["iat"] - 3600 < 2


def assert_is_unauthorized_error(response, message: str):
    """Check that the response is a "401 unauthorized" error."""
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authorization" not in response.headers
    assert response.json() == {"detail": message}


def assert_is_forbidden_error(response, message: str):
    """Check that the response is a "403 forbidden" error."""
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Authorization" not in response.headers
    assert response.json() == {"detail": message}


async def test_get_from_root(bare_client: BareClient):
    """Test that a simple GET request passes."""
    response = await bare_client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" not in response.headers


async def test_get_from_some_path(bare_client: BareClient):
    """Test that a simple GET request passes."""
    response = await bare_client.get("/some/path")

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" not in response.headers


async def test_get_from_some_path_with_query_parameters(bare_client: BareClient):
    """Test that a simple GET request passes."""
    response = await bare_client.get("/some/path?foo=1&bar=2")

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" not in response.headers


async def test_patch_to_some_path(bare_client: BareClient):
    """Test that a PATCH request to a random path passes."""
    response = await bare_client.patch("/some/path")

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" not in response.headers


async def test_post_to_some_path(bare_client: BareClient):
    """Test that a POST request to a random path passes."""
    response = await bare_client.post("/some/path")

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" not in response.headers


async def test_delete_to_some_path(bare_client: BareClient):
    """Test that a DELETE request to a random path passes."""
    response = await bare_client.delete("/some/path")

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" not in response.headers


async def test_basic_auth(client_with_basic_auth: ClientWithBasicAuth):
    """Test that the root path can be protected with basic authentication."""
    client, credentials = client_with_basic_auth

    response = await client.get("/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == 'Basic realm="GHGA Data Portal"'
    assert response.text == "GHGA Data Portal: Not authenticated"

    auth = b64encode(b"bad:credentials").decode("ASCII")
    auth = f"Basic {auth}"
    response = await client.get("/", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == 'Basic realm="GHGA Data Portal"'
    assert response.text == "GHGA Data Portal: Incorrect username or password"

    auth = b64encode(credentials.encode("UTF-8")).decode("ASCII")
    auth = f"Basic {auth}"
    response = await client.get("/", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert response.headers["Authorization"] == ""


async def test_allowed_paths(client_with_basic_auth: ClientWithBasicAuth):
    """Test that allowed paths are excluded from authentication."""
    client = client_with_basic_auth.bare_client

    response = await client.get(
        "/allowed/read/some/thing", headers={"Authorization": "Bearer foo"}
    )
    # access should be allowed without basic authentication
    assert response.status_code == status.HTTP_200_OK
    assert not response.text

    # and authorization headers should be passed through
    assert response.headers["Authorization"] == "Bearer foo"

    response = await client.head("/allowed/read/some/thing")
    assert response.status_code == status.HTTP_200_OK

    response = await client.options("/allowed/read/some/thing")
    assert response.status_code == status.HTTP_200_OK

    response = await client.post(
        "/allowed/write/some/thing", headers={"Authorization": "Bearer bar"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert response.headers["Authorization"] == "Bearer bar"

    response = await client.patch("/allowed/write/some/thing")
    assert response.status_code == status.HTTP_200_OK

    response = await client.delete("/allowed/write/some/thing")
    assert response.status_code == status.HTTP_200_OK

    response = await client.post("/allowed/read/some/thing")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "GHGA Data Portal: Not authenticated"

    response = await client.delete("/allowed/read/some/thing")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = await client.get("/allowed/write/some/thing")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "GHGA Data Portal: Not authenticated"

    response = await client.options("/allowed/write/some/thing")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = await client.post("/not-allowed/some/thing")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "GHGA Data Portal: Not authenticated"


async def test_basic_auth_service_logo(client_with_basic_auth: ClientWithBasicAuth):
    """Test that fetching the service logo is excluded from authentication."""
    client = client_with_basic_auth.bare_client

    response = await client.get("/logo.png")
    assert response.status_code == status.HTTP_200_OK

    response = await client.head("/logo.png")
    assert response.status_code == status.HTTP_200_OK

    response = await client.get("/image.png")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = await client.head("/image.png")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_post_user_without_session(bare_client: BareClient):
    """Test authentication for user registration without a session."""
    response = await bare_client.post(AUTH_PATH + "/users")
    assert_is_unauthorized_error(response, "Not logged in")


async def test_post_user_without_session_and_basic_auth(
    client_with_basic_auth: ClientWithBasicAuth,
):
    """Test valid basic auth but missing session."""
    client, credentials = client_with_basic_auth

    # no basic auth, no session
    response = await client.post(AUTH_PATH + "/users")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == 'Basic realm="GHGA Data Portal"'
    assert response.text == "GHGA Data Portal: Not authenticated"

    # invalid basic auth, no session
    auth = "Basic invalid"
    response = await client.put(
        AUTH_PATH + "/users/some-internal-id", headers={"Authorization": auth}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == 'Basic realm="GHGA Data Portal"'
    assert response.text == "GHGA Data Portal: Invalid authentication credentials"

    # valid basic auth, still no session
    auth = b64encode(credentials.encode("UTF-8")).decode("ASCII")
    auth = f"Basic {auth}"
    response = await client.post(AUTH_PATH + "/users", headers={"Authorization": auth})
    # should give a 403 instead of 401 to distinguish from basic access error
    assert_is_forbidden_error(response, "Not logged in")


async def test_post_user_with_session_and_invalid_csrf(
    client_with_session: ClientWithSession,
):
    """Test user registration with session and invalid CSRF token."""
    client, session = client_with_session[:2]
    session.csrf_token = "invalid"
    response = await client.post(
        AUTH_PATH + "/users", headers=headers_for_session(session)
    )
    assert_is_unauthorized_error(response, "Invalid or missing CSRF token")


async def test_post_user_with_session(bare_client: BareClient, httpx_mock: HTTPXMock):
    """Test user registration with session and valid CSRF token."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)

    app = bare_client.app
    user_dao = DummyUserDao(ext_id="not.john@aai.org")
    app.dependency_overrides[get_user_dao] = lambda: user_dao

    session = await query_new_session(bare_client)
    assert not session.user_id

    response = await bare_client.post(
        AUTH_PATH + "/users", headers=headers_for_session(session)
    )

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    authorization = response.headers["Authorization"]
    assert authorization

    internal_token = get_bearer_token(authorization)
    assert internal_token

    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"id", "name", "email", "title", "exp", "iat", "roles"}

    assert set(claims) == expected_claims
    assert claims["id"] == "john@aai.org"
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["title"] is None
    assert claims["roles"] == []

    iat = claims["iat"]
    assert isinstance(iat, int)
    assert 0 <= now_as_utc().timestamp() - iat < 5
    exp = claims["exp"]
    assert isinstance(exp, int)
    assert 0 <= exp - iat - 3600 < 2


async def test_put_user_without_session(bare_client: BareClient):
    """Test authentication for user update without a session."""
    response = await bare_client.put(AUTH_PATH + "/users/some-internal-id")
    assert_is_unauthorized_error(response, "Not logged in")


async def test_put_user_with_session_and_wrong_user_id(
    client_with_session: ClientWithSession,
):
    """Test user update with session and wrong user ID."""
    client, session = client_with_session[:2]
    response = await client.put(
        AUTH_PATH + "/users/jane@ghga.de", headers=headers_for_session(session)
    )
    assert_is_unauthorized_error(response, "Not registered")


async def test_put_user_with_session_and_invalid_csrf(
    client_with_session: ClientWithSession,
):
    """Test user update with session and invalid CSRF token."""
    client, session = client_with_session[:2]
    session.csrf_token = "invalid"
    response = await client.put(
        AUTH_PATH + "/users/john@ghga.de", headers=headers_for_session(session)
    )
    assert_is_unauthorized_error(response, "Invalid or missing CSRF token")


async def test_put_unregistered_user_with_session(
    bare_client: BareClient,
    httpx_mock: HTTPXMock,
):
    """Test updating an unregistered user with session."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)

    app = bare_client.app
    user_dao = DummyUserDao(ext_id="not.john@aai.org")
    app.dependency_overrides[get_user_dao] = lambda: user_dao

    session = await query_new_session(bare_client)
    assert not session.user_id

    response = await bare_client.put(
        AUTH_PATH + "/users/john@ghga.de", headers=headers_for_session(session)
    )
    assert_is_unauthorized_error(response, "Not registered")


async def test_put_registered_user_with_session(
    bare_client: BareClient, httpx_mock: HTTPXMock
):
    """Test updating a registered user with session."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)

    app = bare_client.app
    user_dao = DummyUserDao()
    app.dependency_overrides[get_user_dao] = lambda: user_dao
    user_token_dao = DummyUserTokenDao()
    app.dependency_overrides[get_user_token_dao] = lambda: user_token_dao
    claim_dao = DummyClaimDao()
    app.dependency_overrides[get_claim_dao] = lambda: claim_dao

    session = await query_new_session(bare_client)
    assert session.user_id == "john@ghga.de"

    response = await bare_client.put(
        AUTH_PATH + "/users/john@ghga.de", headers=headers_for_session(session)
    )

    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    authorization = response.headers["Authorization"]
    assert authorization

    internal_token = get_bearer_token(authorization)
    assert internal_token

    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"id", "name", "email", "title", "exp", "iat", "roles"}

    assert set(claims) == expected_claims
    assert claims["id"] == "john@ghga.de"
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["title"] is None
    assert claims["roles"] == []

    iat = claims["iat"]
    assert isinstance(iat, int)
    assert 0 <= now_as_utc().timestamp() - iat < 5
    exp = claims["exp"]
    assert isinstance(exp, int)
    assert 0 <= exp - iat - 3600 < 2


async def test_random_url_authenticated(client_with_session: ClientWithSession):
    """Test access via internal access token for authenticated users."""
    client, session = client_with_session[:2]
    headers = headers_for_session(session)
    without_csrf = {
        header: value for header, value in headers.items() if "CSRF" not in header
    }

    assert session.state is SessionState.REGISTERED
    # make a query to a random path, with a not fully authenticated session
    response = await client.get("/some/path", headers=headers)
    # this should pass through without yielding an authorization header
    assert response.status_code == status.HTTP_200_OK
    assert "Authorization" not in response.headers
    assert response.headers["X-CSRF-Token"] == ""
    assert response.headers["Cookie"] == ""
    response = await client.get("/some/path", headers=without_csrf)
    assert response.status_code == status.HTTP_200_OK
    assert "Authorization" not in response.headers
    assert "X-CSRF-Token" not in response.headers
    assert response.headers["Cookie"] == ""

    # also try a post request to a random path, with the proper CSRF token
    response = await client.post("/some/path", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert "Authorization" not in response.headers
    assert response.headers["X-CSRF-Token"] == ""
    assert response.headers["Cookie"] == ""
    # however, a post request without a CSRF token should fail
    # even if this is not critical here, since we are not yet fully unauthenticated
    response = await client.post("/some/path", headers=without_csrf)
    assert_is_unauthorized_error(response, "Invalid or missing CSRF token")

    # create second factor and authenticate with that
    response = await client.post(
        AUTH_PATH + "/totp-token",
        json={"user_id": session.user_id, "force": False},
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    totp = get_valid_totp_code(secret)
    response = await client.post(
        AUTH_PATH + "/rpc/verify-totp",
        headers={"X-Authorization": f"Bearer TOTP:{totp}", **headers},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # make a query to a random path, without the session
    response = await client.get("/some/path?foo=1&bar=2")
    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" not in response.headers
    # make a query to a random path, including the session
    response = await client.get("/some/path?foo=1&bar=2", headers=without_csrf)
    assert_has_authorization_header(response, session)

    # make a post request to a random path, without the CSRF token
    response = await client.post("/some/path", headers=without_csrf)
    assert_is_unauthorized_error(response, "Invalid or missing CSRF token")
    # make a post request to a random path, with the CSRF token
    response = await client.post("/some/path", headers=headers)
    assert_has_authorization_header(response, session)

    # make a put request to a random path, without the CSRF token
    response = await client.put("/some/path", headers=without_csrf)
    assert_is_unauthorized_error(response, "Invalid or missing CSRF token")
    # make a put request to a random path, with the CSRF token
    response = await client.put("/some/path", headers=headers)
    assert_has_authorization_header(response, session)

    # make a delete request to a random path, without the CSRF token
    response = await client.delete("/some/path", headers=without_csrf)
    assert_is_unauthorized_error(response, "Invalid or missing CSRF token")
    # make a delete request to a random path, with the CSRF token
    response = await client.delete("/some/path", headers=headers)
    assert_has_authorization_header(response, session)


async def test_log_auth_info(
    client_with_session: ClientWithSession, caplog: pytest.LogCaptureFixture
):
    """Test that the authorization information is logged."""
    client, session = client_with_session[:2]
    headers = headers_for_session(session)
    response = await client.post(
        AUTH_PATH + "/totp-token",
        json={"user_id": session.user_id, "force": False},
        headers=headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    totp = get_valid_totp_code(secret)
    response = await client.post(
        AUTH_PATH + "/rpc/verify-totp",
        headers={"X-Authorization": f"Bearer TOTP:{totp}", **headers},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    caplog.set_level(logging.INFO)
    caplog.clear()

    response = await client.put("/some/path", headers=headers)
    assert_has_authorization_header(response, session)

    records = [record for record in caplog.records if record.module == "auth"]
    assert len(records) == 1
    record: Any = records[0]
    assert record.message == "User authorized"
    assert record.method == "PUT"
    assert record.path == "/some/path"
    assert record.user == session.user_id
    assert record.roles == session.roles
