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
    """Test that GET From well-known path is excluded from basic authentication."""

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
