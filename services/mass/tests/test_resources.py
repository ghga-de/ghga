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


import pytest

from mass.core import models
from mass.ports.inbound.query_handler import (
    ClassNotConfiguredError,
    DeletionFailedError,
    SearchError,
)
from tests.fixtures.config import get_config
from tests.fixtures.joint import JointFixture


@pytest.mark.asyncio
async def test_basic_query(joint_fixture: JointFixture):
    """Make sure we can pull back the documents as expected"""

    # pull back all 3 test documents
    query_handler = await joint_fixture.container.query_handler()
    results = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )

    assert results.count == 3


@pytest.mark.asyncio
async def test_text_search(joint_fixture: JointFixture):
    """Test basic text search"""

    query_handler = await joint_fixture.container.query_handler()
    results_text = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="poolside", filters=[]
    )

    assert results_text.count == 1
    assert results_text.hits[0].id_ == "1HotelAlpha-id"


@pytest.mark.asyncio
async def test_filters_work(joint_fixture: JointFixture):
    """Test a query with filters selected but no query string"""

    query_handler = await joint_fixture.container.query_handler()
    results_filtered = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="",
        filters=[models.Filter(key="field1", value="Amsterdam")],
    )

    assert results_filtered.count == 1
    assert results_filtered.hits[0].id_ == "3zoo-id"

    results_multi_filter = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="",
        filters=[
            models.Filter(key="category", value="hotel"),
            models.Filter(key="has_object.type", value="piano"),
        ],
    )

    assert results_multi_filter.count == 1
    assert results_multi_filter.hits[0].id_ == "1HotelAlpha-id"


@pytest.mark.asyncio
async def test_facets_returned(joint_fixture: JointFixture):
    """Verify that facet fields are returned correctly"""
    query_handler = await joint_fixture.container.query_handler()
    results_faceted = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="",
        filters=[models.Filter(key="category", value="hotel")],
    )

    config = get_config()
    facets: list[models.FacetLabel] = config.searchable_classes[
        "DatasetEmbedded"
    ].facetable_properties
    facet_key_to_name = {x.key: x.name for x in facets}

    for facet in results_faceted.facets:
        assert facet.key in facet_key_to_name
        assert facet.name == facet_key_to_name[facet.key]
        if facet.key == "category":
            assert len(facet.options) == 1
            assert facet.options["hotel"] == 2
        elif facet.key == "field1":
            assert len(facet.options) == 2
            assert facet.options["Miami"] == 1
            assert facet.options["Denver"] == 1
        else:
            assert len(facet.options) == 2
            assert facet.options["piano"] == 1
            assert facet.options["kitchen"] == 1


@pytest.mark.asyncio
async def test_limit_parameter(joint_fixture: JointFixture):
    """Test that the limit parameter works"""
    query_handler = await joint_fixture.container.query_handler()
    results_limited = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[], limit=2
    )
    assert len(results_limited.hits) == 2


@pytest.mark.asyncio
async def test_skip_parameter(joint_fixture: JointFixture):
    """Test that the skip parameter works"""
    query_handler = await joint_fixture.container.query_handler()
    results_skip = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[], skip=1
    )
    assert len(results_skip.hits) == 2
    assert [x.id_ for x in results_skip.hits] == ["2HotelBeta-id", "3zoo-id"]


@pytest.mark.asyncio
async def test_all_parameters(joint_fixture: JointFixture):
    """sanity check - make sure it all works together"""
    query_handler = await joint_fixture.container.query_handler()
    results_all = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="hotel",
        filters=[models.Filter(key="category", value="hotel")],
        skip=1,
        limit=1,
    )

    assert len(results_all.hits) == 1
    assert results_all.hits[0].id_ == "2HotelBeta-id"


@pytest.mark.asyncio
async def test_resource_load(joint_fixture: JointFixture):
    """Test the load function in the query handler"""
    query_handler = await joint_fixture.container.query_handler()

    # get all the documents in the collection
    results_all = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )

    # define and load a new resource
    resource = models.Resource(
        id_="added-resource",
        content={
            "has_object": {"type": "added-resource-object", "id": "98u44-f4jo4"},
            "field1": "something",
            "category": "test object",
        },
    )

    await query_handler.load_resource(resource=resource, class_name="DatasetEmbedded")

    # make sure the new resource is added to the collection
    results_after_load = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )
    assert results_after_load.count - results_all.count == 1

    target_search = await query_handler.handle_query(
        class_name="DatasetEmbedded",
        query="added-resource",
        filters=[],
        skip=0,
        limit=0,
    )
    assert len(target_search.hits) == 1
    validated_resource = target_search.hits[0]
    assert validated_resource.id_ == resource.id_
    assert validated_resource.content == resource.content


@pytest.mark.asyncio
async def test_error_from_malformed_resource(joint_fixture: JointFixture):
    """Make sure we get an error when the DB has malformed content, since that has to be fixed"""
    query_handler = await joint_fixture.container.query_handler()

    # define and load a new resource without all the required facets
    resource = models.Resource(
        id_="added-resource",
        content={
            "has_object": {"type": "added-resource-object", "id": "98u44-f4jo4"},
            "field3": "something",  # expects field1 to exist
            "category": "test object",
        },
    )

    await query_handler.load_resource(resource=resource, class_name="DatasetEmbedded")

    with pytest.raises(SearchError):
        await query_handler.handle_query(
            class_name="DatasetEmbedded", query="", filters=[]
        )


@pytest.mark.asyncio
async def test_absent_resource(joint_fixture: JointFixture):
    """Make sure we get an error when looking for a resource type that doesn't exist"""
    query_handler = await joint_fixture.container.query_handler()
    with pytest.raises(ClassNotConfiguredError):
        await query_handler.handle_query(
            class_name="does_not_exist", query="", filters=[]
        )


@pytest.mark.asyncio
async def test_resource_deletion(joint_fixture: JointFixture):
    """Make sure we can delete a resource.

    Verify that the targeted resource is deleted and nothing else.
    """

    query_handler = await joint_fixture.container.query_handler()
    all_resources = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )

    assert all_resources.count > 1
    await query_handler.delete_resource(
        resource_id="1HotelAlpha-id", class_name="DatasetEmbedded"
    )

    # see if deletion occurred, and make sure only one item was deleted
    results_after_deletion = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )
    assert all_resources.count - results_after_deletion.count == 1

    # make extra sure the resource that got deleted was the correct one
    for resource in results_after_deletion.hits:
        assert resource.id_ != "1HotelAlpha-id"


@pytest.mark.asyncio
async def test_resource_deletion_failure(joint_fixture: JointFixture):
    """Test for correct errors when failing to delete a resource"""

    query_handler = await joint_fixture.container.query_handler()
    all_resources = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )

    assert all_resources.count > 0

    # try to delete a resource that doesn't exist
    with pytest.raises(DeletionFailedError):
        await query_handler.delete_resource(
            resource_id="not-here", class_name="DatasetEmbedded"
        )

    # verify that nothing was actually deleted
    all_resources_again = await query_handler.handle_query(
        class_name="DatasetEmbedded", query="", filters=[]
    )

    assert all_resources_again.count == all_resources.count


@pytest.mark.asyncio
async def test_resource_deletion_not_configured(joint_fixture: JointFixture):
    """Test for correct error when trying to delete a non-configured resource"""
    query_handler = await joint_fixture.container.query_handler()

    with pytest.raises(ClassNotConfiguredError):
        await query_handler.delete_resource(
            resource_id="1HotelAlpha-id", class_name="Not-Configured"
        )
