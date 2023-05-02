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

"""Test the query_resource module."""

import pytest
from hexkit.providers.mongodb.testutils import mongodb_fixture  # noqa: F401
from hexkit.providers.mongodb.testutils import MongoDbFixture

from metldata.artifacts_rest.query_resources import query_artifact_resource
from tests.artifact_rest.test_load_artifacts import load_example_artifact_resources
from tests.fixtures.artifact_info import MINIMAL_ARTIFACT_INFO


@pytest.mark.asyncio
async def test_query_artifact_resource(mongodb_fixture: MongoDbFixture):  # noqa: F811
    """Test happy path of using the query_artifact_resource function."""

    # load example resources and prepare client:
    dao_collection = await load_example_artifact_resources(
        dao_factory=mongodb_fixture.dao_factory
    )

    # Get an example resource:
    artifact_name = MINIMAL_ARTIFACT_INFO.name
    class_name = "File"
    resource_id = "test_sample_01_R1"
    observed_resource = await query_artifact_resource(
        artifact_name=artifact_name,
        class_name=class_name,
        resource_id=resource_id,
        dao_collection=dao_collection,
    )

    # check that the right object was return using an example slot:
    expected_checksum = (
        "1c8aed294d5dec3740a175f6b655725fa668bfe41311e74f7ca9d85c91371b4e"
    )
    assert observed_resource.content["checksum"] == expected_checksum
    # check that the ID is included in the resource:
    assert observed_resource.content["alias"] == resource_id
