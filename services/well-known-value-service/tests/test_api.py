# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Basic tests for the API"""
import pytest
from fastapi import status

from tests.fixtures.joint import JointFixture, joint_fixture  # noqa: F401


@pytest.mark.asyncio
async def test_health_check(joint_fixture: JointFixture):  # noqa: F811
    """Test that the health check endpoint works."""
    response = await joint_fixture.rest_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


@pytest.mark.asyncio
async def test_happy_retrieval(joint_fixture: JointFixture):  # noqa: F811
    """Test that configured values can be retrieved"""
    url = "/values/crypt4gh_public_key"
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "crypt4gh_public_key": "dWoWghAEVPcpHILEb5drJx59nF+of6YKuAOhKRpmegY="
    }


@pytest.mark.parametrize(
    "value_name",
    [
        "not_configured",  # non-existent value
        "service_name",  # existing config value that shouldn't be retrievable
    ],
)
@pytest.mark.asyncio
async def test_non_configured_value(
    joint_fixture: JointFixture, value_name: str  # noqa: F811
):
    """Test that we get an HTTP exception when requesting a non-configured value"""
    url = f"/values/{value_name}"
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"The value {value_name} is not configured"


@pytest.mark.asyncio
async def test_retrieve_all_values(joint_fixture: JointFixture):  # noqa: F811
    """Test that the all-values endpoint works"""
    response = await joint_fixture.rest_client.get("/values")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "crypt4gh_public_key": "dWoWghAEVPcpHILEb5drJx59nF+of6YKuAOhKRpmegY=",
        "wps_api_url": "http://127.0.0.1",
        "dcs_api_url": "http://127.0.0.1/download",
        "ucs_api_url": "http://127.0.0.1/upload",
    }
