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

from mass.adapters.outbound.aggregator import AggregatorNotFoundError
from mass.core import models
from tests.fixtures.joint import JointFixture, joint_fixture  # noqa: F401
from tests.fixtures.mongo import populated_mongodb_fixture  # noqa: F401


@pytest.mark.asyncio
async def test_basic_query(joint_fixture: JointFixture):  # noqa: F811
    """Make sure we can pull back the documents as expected"""

    # pull back all 3 test documents
    query_handler = await joint_fixture.container.query_handler()
    results = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )

    assert len(results) == 3


@pytest.mark.asyncio
async def test_text_search(joint_fixture: JointFixture):  # noqa: F811
    """Test basic text search"""

    query_handler = await joint_fixture.container.query_handler()
    results_text = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="poolside", filters=[]
    )

    assert len(results_text) == 1
    assert results_text[0].id_ == "1HotelAlpha-id"


@pytest.mark.asyncio
async def test_filters_work(joint_fixture: JointFixture):  # noqa: F811
    """Test a query with filters selected but no query string"""

    query_handler = await joint_fixture.container.query_handler()
    results_filtered = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="",
        filters=[models.Filter(key="field1", value="Amsterdam")],
    )

    assert len(results_filtered) == 1
    assert results_filtered[0].id_ == "3zoo-id"

    results_multi_filter = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="",
        filters=[
            models.Filter(key="category", value="hotel"),
            models.Filter(key="has_object.type", value="piano"),
        ],
    )

    assert len(results_filtered) == 1
    assert results_multi_filter[0].id_ == "1HotelAlpha-id"


@pytest.mark.asyncio
async def test_limit_parameter(joint_fixture: JointFixture):  # noqa: F811
    """Test that the limit parameter works"""
    query_handler = await joint_fixture.container.query_handler()
    results_limited = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[], limit=2
    )
    assert len(results_limited) == 2


@pytest.mark.asyncio
async def test_skip_parameter(joint_fixture: JointFixture):  # noqa: F811
    """Test that the skip parameter works"""
    query_handler = await joint_fixture.container.query_handler()
    results_skip = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[], skip=1
    )
    assert len(results_skip) == 2
    assert [x.id_ for x in results_skip] == ["2HotelBeta-id", "3zoo-id"]


@pytest.mark.asyncio
async def test_all_parameters(joint_fixture: JointFixture):  # noqa: F811
    """sanity check - make sure it all works together"""
    query_handler = await joint_fixture.container.query_handler()
    results_all = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="hotel",
        filters=[models.Filter(key="category", value="hotel")],
        skip=1,
        limit=1,
    )

    assert len(results_all) == 1
    assert results_all[0].id_ == "2HotelBeta-id"


@pytest.mark.asyncio
async def test_resource_load(joint_fixture: JointFixture):  # noqa: F811
    """Test the load function in the query handler"""
    query_handler = await joint_fixture.container.query_handler()

    # get all the documents in the collection
    results_all = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )

    # define and load a new resource
    resource = models.Resource(
        id_="jf2jl-dlasd82",
        content={
            "has_feature": {"feature_name": "added_resource", "id": "98u44-f4jo4"}
        },
    )

    await query_handler.load_resource(resource=resource, class_name="DatasetEmbedded")

    # make sure the new resource is added to the collection
    results_after_load = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )
    assert len(results_after_load) - len(results_all) == 1

    target_search = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="added_resource",
        filters=[],
        skip=0,
        limit=0,
    )
    assert len(target_search) == 1
    validated_resource = target_search[0]
    assert validated_resource.id_ == resource.id_
    assert validated_resource.content == resource.content


@pytest.mark.asyncio
async def test_absent_resource(joint_fixture: JointFixture):  # noqa: F811
    """Make sure we get an error when looking for a resource type that doesn't exist"""
    query_handler = await joint_fixture.container.query_handler()
    with pytest.raises(AggregatorNotFoundError):
        await query_handler.handle_query(
            class_name="does_not_exist",
            query="",
            filters=[],
            skip=0,
            limit=0,
        )
