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

"""Basic tests for presence of resources/documents in the database"""

# pylint: disable=redefined-outer-name

import pytest
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    MongoDbFixture,
    mongodb_fixture,
)

from mass.adapters.outbound.dao import DaoNotFoundError
from mass.core import models
from tests.fixtures.joint import JointFixture, joint_fixture  # noqa: F401
from tests.fixtures.mongo import populated_mongodb_fixture  # noqa: F401


@pytest.mark.asyncio
async def test_basic_query_and_load(joint_fixture: JointFixture):  # noqa: F811
    """Make sure we can pull back the documents that are stored as well as load more"""

    query_handler = await joint_fixture.container.query_handler()
    results_dataset_embedded = await query_handler.handle_query(
        class_name="DatasetEmbedded"
    )
    assert len(results_dataset_embedded) > 0

    resource = models.Resource(
        id_="jf2jl-dlasd82",
        content={
            "has_color": ["red"],
            "has_features": ["starchy", "round"],
        },
    )
    await query_handler.load_resource(resource=resource, class_name="DatasetEmbedded")
    results_dataset_embedded_2 = await query_handler.handle_query(
        class_name="DatasetEmbedded"
    )
    assert len(results_dataset_embedded_2) - len(results_dataset_embedded) == 1


@pytest.mark.asyncio
async def test_absent_resource(joint_fixture: JointFixture):  # noqa: F811
    """Make sure we get an error when looking for a resource type that doesn't exist"""
    query_handler = await joint_fixture.container.query_handler()
    with pytest.raises(DaoNotFoundError):
        await query_handler.handle_query(class_name="raccoon")
