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
from fastapi.testclient import TestClient

from auth_service.user_management.api.main import app


def test_get_from_root():
    """Test that a simple GET request passes."""

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == '"Hello World from the User Management."'


def test_get_from_some_other_path():
    """Test that a GET request to a random path raises a not found error."""

    client = TestClient(app)
    response = client.post("/some/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND
