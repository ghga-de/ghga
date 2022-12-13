# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

from base64 import b64encode

from fastapi import status
from ghga_service_chassis_lib.utils import now_as_utc

from auth_service.auth_adapter.api.headers import get_bearer_token
from auth_service.config import CONFIG
from auth_service.user_management.claims_repository.deps import ClaimDao, get_claim_dao
from auth_service.user_management.user_registry.deps import UserDao, get_user_dao
from auth_service.user_management.user_registry.models.dto import UserStatus

from ...fixtures.utils import (
    DummyClaimDao,
    DummyUserDao,
    create_access_token,
    get_claims_from_token,
)
from .fixtures import (  # noqa: F401; pylint: disable=unused-import
    fixture_client,
    fixture_with_basic_auth,
)

API_EXT_PATH = CONFIG.api_ext_path.strip("/")
if API_EXT_PATH:
    API_EXT_PATH += "/"
USERS_PATH = f"/{API_EXT_PATH}users"


def test_get_from_root(client):
    """Test that a simple GET request passes."""

    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


def test_get_from_some_path(client):
    """Test that a simple GET request passes."""

    response = client.get("/some/path")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


def test_get_from_some_path_with_query_parameters(client):
    """Test that a simple GET request passes."""

    response = client.get("/some/path?foo=1&bar=2")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


def test_patch_to_some_path(client):
    """Test that a PATCH request to a random path passes."""

    response = client.patch("/some/path")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


def test_post_to_some_path(client):
    """Test that a POST request to a random path passes."""

    response = client.post("/some/path")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


def test_delete_to_some_path(client):
    """Test that a DELETE request to a random path passes."""

    response = client.delete("/some/path")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


def test_basic_auth(with_basic_auth, client):
    """Test that the root path can be protected with basic authentication."""

    response = client.get("/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == 'Basic realm="GHGA Data Portal"'
    assert response.text == "GHGA Data Portal: Not authenticated"

    auth = b64encode(b"bad:credentials").decode("ASCII")
    auth = f"Basic {auth}"
    response = client.get("/", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == 'Basic realm="GHGA Data Portal"'
    assert response.text == "GHGA Data Portal: Incorrect username or password"

    auth = b64encode(with_basic_auth.encode("UTF-8")).decode("ASCII")
    auth = f"Basic {auth}"
    response = client.get("/", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


def test_basic_auth_well_known(with_basic_auth, client):
    """Test that GET from well-known path is excluded from basic authentication."""

    assert with_basic_auth

    response = client.get("/.well-known/some/thing")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    response = client.post("/.well-known/some/thing")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "GHGA Data Portal: Not authenticated"

    response = client.get("/.not-well-known/some/thing")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == "GHGA Data Portal: Not authenticated"


def test_does_not_authorize_invalid_users(client):
    """Test that unauthenticated or invalid users are not authorized."""

    # User without Authorization token
    response = client.get("/some/path")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert "Authorization" in headers
    assert headers["Authorization"] == ""
    assert "X-Authorization" not in headers

    # User with empty Authorization token
    response = client.get("/some/path", headers={"Authorization": ""})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert "Authorization" in headers
    assert headers["Authorization"] == ""
    assert "X-Authorization" not in headers

    # User with non-bearer Authorization token
    response = client.get("/some/path", headers={"Authorization": "Foo bar"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert "Authorization" in headers
    assert headers["Authorization"] == ""
    assert "X-Authorization" not in headers

    # User with empty bearer Authorization token
    response = client.get("/some/path", headers={"Authorization": "Bearer"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert "Authorization" in headers
    assert headers["Authorization"] == ""
    assert "X-Authorization" not in headers

    # User with invalid bearer Authorization token
    response = client.get("/some/path", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid access token"}

    headers = response.headers
    assert "Authorization" not in headers
    assert "X-Authorization" not in headers

    # User with invalid bearer X-Authorization token
    response = client.get("/some/path", headers={"Authorization": "Bearer invalid"})
    response = client.get(
        "/some/path",
        headers={"Authorization": "Basic invalid", "X-Authorization": "Bearer invalid"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid access token"}

    headers = response.headers
    assert "Authorization" not in headers
    assert "X-Authorization" not in headers


def test_token_exchange_for_unknown_user(
    client,
):  # pylint:disable=too-many-statements
    """Test the token exchange for authenticated but unknown users."""

    user_dao = DummyUserDao(ls_id="not.john@aai.org")
    client.app.dependency_overrides[get_user_dao] = lambda: user_dao

    auth = f"Bearer {create_access_token()}"

    # does not get internal token for GET request to random path
    response = client.get("/some/path", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert headers.get("Authorization") == ""
    assert "X-Authorization" not in headers

    # does not get internal token for POST request to random path
    response = client.post("/some/path", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert headers.get("Authorization") == ""
    assert "X-Authorization" not in headers

    # does not get internal token for GET request to users
    response = client.get(USERS_PATH, headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert headers.get("Authorization") == ""
    assert "X-Authorization" not in headers

    # does not get internal token for GET request to users with internal ID
    response = client.get(
        f"{USERS_PATH}/some-internal-id", headers={"Authorization": auth}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert headers.get("Authorization") == ""
    assert "X-Authorization" not in headers

    # gets internal token for GET request to users with external ID
    response = client.get(
        f"{USERS_PATH}/someone@aai.org", headers={"Authorization": auth}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    authorization = headers.get("Authorization")
    assert authorization
    assert "X-Authorization" not in headers

    internal_token = get_bearer_token(authorization)
    assert internal_token
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"name", "email", "ls_id", "exp", "iat"}

    assert set(claims) == expected_claims
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["ls_id"] == "john@aai.org"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]

    # gets internal token for POST request to users
    response = client.post(USERS_PATH, headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    authorization = headers.get("Authorization")
    assert authorization
    assert "X-Authorization" not in headers

    internal_token = get_bearer_token(authorization)
    assert internal_token
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"name", "email", "ls_id", "exp", "iat"}

    assert set(claims) == expected_claims
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["ls_id"] == "john@aai.org"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]


def test_token_exchange_for_known_user(
    client,
):  # pylint:disable=too-many-statements
    """Test the token exchange for authenticated and registered users."""

    user_dao: UserDao = DummyUserDao()
    client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    claim_dao: ClaimDao = DummyClaimDao()
    client.app.dependency_overrides[get_claim_dao] = lambda: claim_dao
    user = user_dao.user

    # Check that we get an internal token for the user

    auth = f"Bearer {create_access_token()}"
    response = client.get("/some/path", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    authorization = headers.get("Authorization")
    assert authorization
    assert "X-Authorization" not in headers

    internal_token = get_bearer_token(authorization)
    assert internal_token
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"id", "name", "email", "status", "exp", "iat"}

    assert set(claims) == expected_claims
    assert claims["id"] == user.id
    assert claims["name"] == user.name
    assert claims["email"] == user.email
    assert claims["status"] == "activated"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]

    # Check that the user is inactivated when the name has changed
    assert user.status is UserStatus.ACTIVATED
    assert user.status_change is None

    auth = f"Bearer {create_access_token(name='John Foo')}"
    response = client.get("/some/path", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    authorization = headers.get("Authorization")
    assert authorization
    assert "X-Authorization" not in headers

    internal_token = get_bearer_token(authorization)
    assert internal_token
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"id", "name", "email", "status", "exp", "iat"}

    assert set(claims) == expected_claims
    assert claims["id"] == user.id
    assert claims["name"] == "John Foo"  # changed name in internal token
    assert claims["email"] == user.email
    assert claims["status"] == "inactivated"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]

    # Check that the status was also changed in the database
    user = user_dao.user
    assert user.name == "John Doe"  # user name was not changed
    assert user.status == UserStatus.INACTIVATED
    status_change = user.status_change
    assert status_change is not None
    assert status_change.previous is UserStatus.ACTIVATED
    assert status_change.by is None
    assert status_change.context == "name changed"
    assert 0 <= (now_as_utc() - status_change.change_date).total_seconds() < 5


def test_token_exchange_with_x_token(client):
    """Test that the external access token can be passed in separate header."""

    user_dao = DummyUserDao(ls_id="not.john@aai.org")
    client.app.dependency_overrides[get_user_dao] = lambda: user_dao

    auth = f"Bearer {create_access_token()}"

    # send access token to some path in X-Authorization header
    response = client.get("/some/path", headers={"X-Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert headers.get("Authorization") == ""
    assert "X-Authorization" not in headers

    # send access token in POST request to users to get the internal token
    response = client.post(USERS_PATH, headers={"X-Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    authorization = headers.get("Authorization")
    assert authorization
    assert "X-Authorization" not in headers

    internal_token = get_bearer_token(authorization)
    assert internal_token
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"name", "email", "ls_id", "exp", "iat"}

    assert set(claims) == expected_claims
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["ls_id"] == "john@aai.org"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]


def test_token_exchange_for_known_data_steward(
    client,
):  # pylint:disable=too-many-statements
    """Test the token exchange for an authenticated data steward."""

    # add a dummy user who is a data steward
    user_dao: UserDao = DummyUserDao(id_="james@ghga.de")
    client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    claim_dao: ClaimDao = DummyClaimDao()
    client.app.dependency_overrides[get_claim_dao] = lambda: claim_dao
    user = user_dao.user

    auth = f"Bearer {create_access_token()}"
    response = client.get("/some/path", headers={"Authorization": auth})
    assert response.status_code == status.HTTP_200_OK

    headers = response.headers
    authorization = headers.get("Authorization")
    assert authorization

    internal_token = get_bearer_token(authorization)
    assert internal_token
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"id", "name", "email", "status", "exp", "iat", "role"}

    assert set(claims) == expected_claims
    assert claims["id"] == user.id
    assert claims["name"] == user.name
    assert claims["email"] == user.email
    assert claims["status"] == "activated"

    # check that the data steward role appears in the token
    assert claims["role"] == "data_steward"
