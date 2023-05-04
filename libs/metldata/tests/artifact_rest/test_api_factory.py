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
#

"""Test the api_factory module."""


import httpx
import pytest
from fastapi import FastAPI
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.providers.mongodb.testutils import mongodb_fixture  # noqa: F401
from hexkit.providers.mongodb.testutils import MongoDbFixture

from metldata.artifacts_rest.api_factory import rest_api_factory
from metldata.artifacts_rest.artifact_info import ArtifactInfo
from tests.artifact_rest.test_load_artifacts import load_example_artifact_resources
from tests.fixtures.artifact_info import EXAMPLE_ARTIFACT_INFOS, MINIMAL_ARTIFACT_INFO


@pytest.mark.asyncio
async def get_example_app_client(
    dao_factory: DaoFactoryProtocol,
    artifact_infos: list[ArtifactInfo] = EXAMPLE_ARTIFACT_INFOS,
) -> httpx.AsyncClient:
    """Return a test client for a FastAPI generated using the artifact_rest_factory."""

    router = await rest_api_factory(
        artifact_infos=artifact_infos, dao_factory=dao_factory
    )

    app = FastAPI()
    app.include_router(router)
    return AsyncTestClient(app)


@pytest.mark.asyncio
async def test_artifacts_info_endpoint(mongodb_fixture: MongoDbFixture):  # noqa: F811
    """Test happy path of using the artifacts info endpoint."""

    expected_infos = EXAMPLE_ARTIFACT_INFOS

    async with await get_example_app_client(
        dao_factory=mongodb_fixture.dao_factory
    ) as client:
        response = await client.options("/artifacts")

    response_json = response.json()
    assert isinstance(response_json, list)
    observed_infos = [ArtifactInfo(**info) for info in response_json]
    assert observed_infos == expected_infos


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "artifact_name, expected_info",
    [(info.name, info) for info in EXAMPLE_ARTIFACT_INFOS],
)
async def test_artifact_info_endpoint(
    artifact_name: str,
    expected_info: ArtifactInfo,
    mongodb_fixture: MongoDbFixture,  # noqa: F811
):
    """Test happy path of using the artifact info endpoint."""

    async with await get_example_app_client(
        dao_factory=mongodb_fixture.dao_factory
    ) as client:
        response = await client.options(f"/artifacts/{artifact_name}")

    observed_info = ArtifactInfo(**response.json())
    assert observed_info == expected_info


@pytest.mark.asyncio
async def test_get_artifact_resource_endpoint(
    mongodb_fixture: MongoDbFixture,  # noqa: F811
):
    """Test happy path of using the get artifact resource endpoint."""

    # load example resources and prepare client:
    await load_example_artifact_resources(dao_factory=mongodb_fixture.dao_factory)

    # Get an example resource:
    artifact_name = MINIMAL_ARTIFACT_INFO.name
    class_name = "File"
    resource_id = "test_sample_01_R1"
    async with await get_example_app_client(
        dao_factory=mongodb_fixture.dao_factory, artifact_infos=[MINIMAL_ARTIFACT_INFO]
    ) as client:
        response = await client.get(
            f"/artifacts/{artifact_name}/classes/{class_name}/resources/{resource_id}"
        )

    assert response.status_code == 200
    observed_resource = response.json()
    # check that the right object was return using an example slot:
    expected_checksum = (
        "1c8aed294d5dec3740a175f6b655725fa668bfe41311e74f7ca9d85c91371b4e"
    )
    assert observed_resource["checksum"] == expected_checksum
    # check that the ID is included in the resource:
    assert observed_resource["alias"] == resource_id
