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

from auth_service.auth_adapter.core.auth import (
    decode_and_verify_token,
    sign_and_encode_token,
    signing_keys,
)

from .fixtures import (  # noqa: F401; pylint: disable=unused-import
    fixture_client,
    fixture_with_basic_auth,
)


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


def test_token_exchange(client):
    """Test that the external access token is exchanged against an internal token."""

    ext_payload = {"name": "Foo Bar", "email": "foo@bar", "sub": "foo", "iss": "bar"}
    ext_sign_keyset = signing_keys.external_jwks
    assert ext_sign_keyset
    ext_sign_key = ext_sign_keyset.get_key("test")
    assert ext_sign_key
    auth = sign_and_encode_token(ext_payload, key=ext_sign_key)
    auth = f"Bearer {auth}"
    response = client.get("/some/path", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert "Authorization" in headers
    internal_token = headers["Authorization"]
    assert internal_token is not None
    assert isinstance(internal_token, str)
    assert internal_token.count(".", 2)

    int_payload = decode_and_verify_token(internal_token, key=signing_keys.internal_jwk)
    assert int_payload == {"name": "Foo Bar", "email": "foo@bar"}

    assert "X-Authorization" not in headers


def test_token_exchange_with_x_token(client):
    """Test that the external access token can be passed in separate header."""

    ext_payload = {"name": "Foo Bar", "email": "foo@bar", "sub": "foo", "iss": "bar"}
    ext_sign_keyset = signing_keys.external_jwks
    assert ext_sign_keyset
    ext_sign_key = ext_sign_keyset.get_key("test")
    assert ext_sign_key
    auth = sign_and_encode_token(ext_payload, key=ext_sign_key)
    auth = f"Bearer {auth}"
    response = client.get("/some/path", headers={"X-Authorization": auth})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert "Authorization" in headers
    internal_token = headers["Authorization"]
    assert internal_token is not None
    assert isinstance(internal_token, str)
    assert internal_token.count(".", 2)

    int_payload = decode_and_verify_token(internal_token, key=signing_keys.internal_jwk)
    assert int_payload == {"name": "Foo Bar", "email": "foo@bar"}

    assert "X-Authorization" not in headers


def test_external_tokens_are_removed(client):
    """Test that the external access token is exchanged against an internal token."""

    response = client.get("/some/path", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert "Authorization" in headers
    assert headers["Authorization"] == ""
    assert "X-Authorization" not in headers

    response = client.get(
        "/some/path",
        headers={"Authorization": "Basic invalid", "X-Authorization": "Bearer invalid"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    headers = response.headers
    assert "Authorization" in headers
    assert headers["Authorization"] == ""
    assert "X-Authorization" not in headers
