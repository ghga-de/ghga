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

"""Test the main modules."""

from copy import deepcopy

import pytest
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError

from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.models import ArtifactInfo, GlobalStats
from metldata.load.auth import generate_token, generate_token_and_hash
from metldata.load.config import ArtifactLoaderAPIConfig
from metldata.load.main import get_app
from metldata.load.stats import STATS_COLLECTION_NAME
from tests.fixtures.artifact_info import EXAMPLE_ARTIFACT_INFOS
from tests.fixtures.mongodb import (  # noqa: F401; pylint: disable=unused-import
    MongoDbFixture,
    mongodb_fixture,
)
from tests.fixtures.workflows import EXAMPLE_ARTIFACTS


async def get_configured_client(
    mongodb_fixture: MongoDbFixture,  # noqa: F811
    artifact_infos: list[ArtifactInfo],
) -> tuple[AsyncTestClient, str]:
    """Get a tuple of a configured test client together with a corresponding token."""

    token, token_hash = generate_token_and_hash()
    config = ArtifactLoaderAPIConfig(
        artifact_infos=artifact_infos,
        loader_token_hashes=[token_hash],
        **mongodb_fixture.config.dict(),
    )
    app = await get_app(config=config)
    client = AsyncTestClient(app)
    return client, token


@pytest.mark.asyncio
async def test_load_artifacts_endpoint_happy(
    mongodb_fixture: MongoDbFixture,  # noqa: F811
):
    """Test the happy path of using the load artifacts endpoint."""

    client, token = await get_configured_client(
        mongodb_fixture=mongodb_fixture, artifact_infos=EXAMPLE_ARTIFACT_INFOS
    )

    # load example artifacts resources:
    artifact_resources = {
        artifact_name: [artifact_content]
        for artifact_name, artifact_content in EXAMPLE_ARTIFACTS.items()
    }

    response = await client.post(
        "/rpc/load-artifacts",
        json=artifact_resources,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # check that the artifact resources were loaded based on an example:
    expected_artifact_name = "inferred_and_public"
    expected_resource_class = "File"
    expected_resource_id = "test_sample_01_R1"
    expected_resource_content = {
        "alias": "test_sample_01_R1",
        "format": "fastq",
        "size": 299943,
    }

    dao_collection = await ArtifactDaoCollection.construct(
        dao_factory=mongodb_fixture.dao_factory,
        artifact_infos=EXAMPLE_ARTIFACT_INFOS,
    )
    dao = await dao_collection.get_dao(
        artifact_name=expected_artifact_name, class_name=expected_resource_class
    )

    observed_resource = await dao.get_by_id(expected_resource_id)
    assert observed_resource.content == expected_resource_content

    # test upsert of changed resource
    expected_resource_content = {
        "alias": "test_sample_01_R1",
        "format": "fastq",
        "size": 123456,
    }
    # replace tested resource with slightly changed one
    new_artifact_resources = deepcopy(artifact_resources)
    new_artifact_resources[expected_artifact_name][0]["files"][
        0
    ] = expected_resource_content

    # submit changed request:
    response = await client.post(
        "/rpc/load-artifacts",
        json=new_artifact_resources,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    observed_resource = await dao.get_by_id(expected_resource_id)
    assert observed_resource.content == expected_resource_content

    # check that the summary statistics has been created:
    expected_resource_stats = {
        "Dataset": {"count": 1},
        "Sample": {"count": 2},
        "File": {"count": 4, "stats": {"format": {"fastq": 4}}},
        "Experiment": {"count": 1},
    }
    stats_dao = await mongodb_fixture.dao_factory.get_dao(
        name=STATS_COLLECTION_NAME, dto_model=GlobalStats, id_field="id"
    )
    async for stats in stats_dao.find_all(mapping={}):
        assert stats.id == "global"
        assert abs((now_as_utc() - stats.created).seconds) < 5
        assert stats.resource_stats == expected_resource_stats

    # submit an empty request:
    response = await client.post(
        "/rpc/load-artifacts",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # confirm that example resource was deleted:
    with pytest.raises(ResourceNotFoundError):
        await dao.get_by_id(expected_resource_id)


@pytest.mark.asyncio
async def test_load_artifacts_endpoint_invalid_resources(
    mongodb_fixture: MongoDbFixture,  # noqa: F811
):
    """Test using the load artifacts endpoint with resources of unknown artifacts."""

    client, token = await get_configured_client(
        mongodb_fixture=mongodb_fixture, artifact_infos=EXAMPLE_ARTIFACT_INFOS
    )

    # load example artifacts resources:
    unknown_artifact_resources = {
        "unknown_artifact": [list(EXAMPLE_ARTIFACTS.values())[0]]
    }
    response = await client.post(
        "/rpc/load-artifacts",
        json=unknown_artifact_resources,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_load_artifacts_endpoint_invalid_token(
    mongodb_fixture: MongoDbFixture,  # noqa: F811
):
    """Test that using the load artifacts endpoint with an invalid token fails."""

    invalid_token = generate_token()
    client, _ = await get_configured_client(
        mongodb_fixture=mongodb_fixture, artifact_infos=EXAMPLE_ARTIFACT_INFOS
    )

    # load artifact resources with invalid token:
    response = await client.post(
        "/rpc/load-artifacts",
        json={},
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == 403
