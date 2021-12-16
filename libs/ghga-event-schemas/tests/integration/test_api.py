# Copyright 2021 Universität Tübingen, DKFZ and EMBL
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

from my_microservice.api.main import app


def test_index():
    """Test the index endpoint"""

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == '"Hello World."'


def test_greet():
    """Test the greet endpoint"""

    name = "Friendly Tester"

    client = TestClient(app)
    response = client.get(f"/greet/{name}")

    assert response.status_code == status.HTTP_200_OK
    assert name in response.json()["message"]
