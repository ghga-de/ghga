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

from fastapi import status

from .fixtures import (  # noqa: F401; pylint: disable=unused-import
    fixture_client,
    fixture_client_with_db,
)


def test_get_from_root(client):
    """Test that a simple GET request passes."""

    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == '"Hello World from the User Management."'


def test_get_from_some_other_path(client):
    """Test that a GET request to a random path raises a not found error."""

    response = client.post("/some/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_demo_create_user(client_with_db):
    """Test that the demo endpoint for creating a user works."""

    response = client_with_db.post("/create_demo_user")

    assert response.status_code == status.HTTP_200_OK
    dto = response.json()

    assert set(dto) == {
        "academic_title",
        "email",
        "id",
        "ls_id",
        "name",
        "registration_date",
        "registration_reason",
        "research_topics",
    }
    assert dto["name"] == "Demo User"
    id_ = dto["id"]
    assert isinstance(id_, str)
    assert len(id_) == 36
    assert id_.count("-") == 4
