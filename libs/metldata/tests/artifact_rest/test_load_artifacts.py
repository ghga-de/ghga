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

"""Test the load_artifacts module"""

import pytest
from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.providers.mongodb.testutils import mongodb_fixture  # noqa: F401
from hexkit.providers.mongodb.testutils import MongoDbFixture

from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.load_resources import load_artifact_resources
from metldata.artifacts_rest.models import ArtifactResource
from tests.fixtures.artifact_info import MINIMAL_ARTIFACT_INFO
from tests.fixtures.metadata import VALID_MINIMAL_METADATA_EXAMPLE


async def load_example_artifact_resources(
    dao_factory: DaoFactoryProtocol,
) -> ArtifactDaoCollection:
    """Load the example artifact using the load_artifact_resources function and
    returns a ArtifactDaoCollection for accessing the resources."""

    # construct the dao collection:
    dao_collection = await ArtifactDaoCollection.construct(
        dao_factory=dao_factory,
        artifact_infos=[MINIMAL_ARTIFACT_INFO],
    )

    # load artifact resources from the metadata example:
    await load_artifact_resources(
        artifact_content=VALID_MINIMAL_METADATA_EXAMPLE,
        artifact_info=MINIMAL_ARTIFACT_INFO,
        dao_collection=dao_collection,
    )

    return dao_collection


@pytest.mark.asyncio
async def test_load_artifact_resources(mongodb_fixture: MongoDbFixture):  # noqa: F811
    """Test happy path of using load_artifact_resources function."""

    dao_collection = await load_example_artifact_resources(
        dao_factory=mongodb_fixture.dao_factory,
    )

    # check that artifact resources have been persisted to the database by testing for
    # an example file:
    expected_resource = ArtifactResource(
        id_="test_sample_01_R1",
        class_name="File",
        content={
            "alias": "test_sample_01_R1",
            "filename": "test_sample_01_R1.fastq",
            "format": "fastq",
            "checksum": "1c8aed294d5dec3740a175f6b655725fa668bfe41311e74f7ca9d85c91371b4e",
            "size": 299943,
        },
    )
    dao = await dao_collection.get_dao(
        artifact_name=MINIMAL_ARTIFACT_INFO.name,
        class_name=expected_resource.class_name,
    )
    observed_resource = await dao.get_by_id(id_=expected_resource.id_)
    assert observed_resource == expected_resource
