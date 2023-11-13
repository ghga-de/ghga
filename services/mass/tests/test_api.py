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

"""Tests to assess API functionality"""

from typing import Optional

import pytest
from hexkit.custom_types import JsonObject

from mass.core import models
from tests.fixtures.config import get_config
from tests.fixtures.joint import JointFixture


def compare(
    *,
    results: models.QueryResults,
    count: int,
    hit_length: int,
    hits: Optional[list[models.Resource]] = None,
    facets: Optional[list[models.Facet]] = None,
) -> None:
    """Perform common comparisons for results"""
    assert results.count == count
    assert len(results.hits) == hit_length

    if not facets:
        config = get_config()

        dataset_embedded_class = config.searchable_classes["DatasetEmbedded"]
        assert dataset_embedded_class is not None

        configured_facets = dataset_embedded_class.facetable_properties
        assert len(results.facets) == len(configured_facets)
        assert {x.key for x in results.facets} == {x.key for x in configured_facets}
    else:
        assert results.facets == facets

    if hits:
        assert results.hits == hits


@pytest.mark.asyncio
async def test_health_check(joint_fixture: JointFixture):
    """Test that the health check endpoint works."""
    response = await joint_fixture.rest_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


@pytest.mark.asyncio
async def test_search_options(joint_fixture: JointFixture):
    """Verify that we can request the configured resource class information correctly"""
    response = await joint_fixture.rest_client.get(url="/rpc/search-options")

    assert response.json() == joint_fixture.config.model_dump()["searchable_classes"]


@pytest.mark.asyncio
async def test_malformed_document(joint_fixture: JointFixture):
    """Test behavior from API perspective upon querying when bad doc exists"""
    joint_fixture.remove_db_data()

    # define and load a new resource without all the required facets
    resource = models.Resource(
        id_="added-resource",
        content={
            "has_object": {"type": "added-resource-object", "id": "98u44-f4jo4"},
            "field3": "something",  # expects field1 to exist
            "category": "test object",
        },
    )

    await joint_fixture.query_handler.load_resource(
        resource=resource, class_name="DatasetEmbedded"
    )
    search_parameters: JsonObject = {
        "class_name": "DatasetEmbedded",
        "query": "",
        "filters": [],
        "skip": 0,
    }

    response = await joint_fixture.rest_client.post(
        url="/rpc/search", json=search_parameters
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_search(joint_fixture: JointFixture):
    """Basic query to pull back all documents for class name"""
    search_parameters: JsonObject = {
        "class_name": "DatasetEmbedded",
        "query": "",
        "filters": [],
        "skip": 0,
    }

    results = await joint_fixture.call_search_endpoint(search_parameters)
    compare(results=results, count=3, hit_length=3)


@pytest.mark.asyncio
async def test_search_with_limit(joint_fixture: JointFixture):
    """Make sure we get a count of 3 but only 1 hit"""
    search_parameters: JsonObject = {
        "class_name": "DatasetEmbedded",
        "query": "",
        "filters": [],
        "skip": 0,
        "limit": 1,
    }

    results = await joint_fixture.call_search_endpoint(search_parameters)
    hit = {
        "id_": "1HotelAlpha-id",
        "content": {
            "category": "hotel",
            "field1": "Miami",
            "has_object": {"id_": "HotelAlphaObject", "type": "piano"},
            "has_rooms": [
                {"id_": "HotelAlphaLarge", "type": "large room"},
                {"id_": "HotelAlphaPoolside", "type": "poolside room"},
            ],
            "type": "resort",
        },
    }
    hits = [models.Resource(**hit)]  # type: ignore[arg-type]
    compare(results=results, count=3, hit_length=1, hits=hits)


@pytest.mark.asyncio
async def test_search_keywords(joint_fixture: JointFixture):
    """Make sure the query string is passed through intact"""
    search_parameters: JsonObject = {
        "class_name": "DatasetEmbedded",
        "query": "hotel",
        "filters": [],
        "skip": 0,
    }

    results = await joint_fixture.call_search_endpoint(search_parameters)
    compare(results=results, count=2, hit_length=2)


@pytest.mark.asyncio
async def test_search_filters(joint_fixture: JointFixture):
    """Make sure filters work"""
    search_parameters: JsonObject = {
        "class_name": "DatasetEmbedded",
        "query": "",
        "filters": [{"key": "has_object.type", "value": "piano"}],
        "skip": 0,
    }

    results = await joint_fixture.call_search_endpoint(search_parameters)
    compare(results=results, count=1, hit_length=1)


@pytest.mark.asyncio
async def test_search_invalid_class(joint_fixture: JointFixture):
    """Verify that searching with a bad class name results in a 422"""
    search_parameters: JsonObject = {
        "class_name": "InvalidClassName",
        "query": "",
        "filters": [],
        "skip": 0,
        "limit": 1,
    }

    response = await joint_fixture.rest_client.post(
        url="/rpc/search", json=search_parameters
    )
    assert response.status_code == 422
