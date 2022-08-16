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

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.text == '"Hello World from the Auth Adapter."'


def test_post_to_some_path(client):
    """Test that a POST request to a random path passes."""

    response = client.post("/some/path")

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.text == '"Hello World from the Auth Adapter."'


def test_basic_auth(with_basic_auth, client):
    """Test that the root path can be protected with basic authentication."""

    response = client.get("/")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text
    assert response.headers["WWW-Authenticate"] == 'Basic realm="GHGA Data Portal"'

    auth = b64encode(b"bad:credentials").decode("ASCII")
    auth = f"Basic {auth}"
    response = client.get("/", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text
    assert response.headers["WWW-Authenticate"] == 'Basic realm="GHGA Data Portal"'

    auth = b64encode(with_basic_auth.encode("UTF-8")).decode("ASCII")
    auth = f"Basic {auth}"
    response = client.get("/", headers={"Authorization": auth})

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.text == '"Hello World from the Auth Adapter."'
