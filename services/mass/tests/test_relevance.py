# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Tests for relevance sorting"""

import pytest

from mass.core import models
from tests.fixtures.joint import JointFixture, QueryParams

pytestmark = pytest.mark.asyncio()

CLASS_NAME: str = "RelevanceTests"
RELEVANCE_SORT = models.SortingParameter(
    field="score", order=models.SortOrder.RELEVANCE
)
ID_ASC = models.SortingParameter(field="_id", order=models.SortOrder.ASCENDING)
ID_DESC = models.SortingParameter(field="_id", order=models.SortOrder.DESCENDING)
FIELD_ASC = models.SortingParameter(field="field", order=models.SortOrder.ASCENDING)


def multi_column_sort(
    results: list[dict], sorts: list[models.SortingParameter]
) -> list[dict]:
    """This is equivalent to nested sorted() calls.

    This uses the same approach as the sorting function in test_sorting, but the
    difference is that this function uses the raw dicts returned by the MongoClient and
    is meant to work with the textScore attribute.

    The sorting parameters are supplied in order of most significant to least significant,
    so we take them off the front and apply sorted(). If there are more parameters to
    apply (more sorts), we recurse until we apply the final parameter. The sorted lists
    are passed back up the call chain.
    """
    sorted_list = results.copy()
    parameter = sorts[0]
    del sorts[0]

    if parameter.order == models.SortOrder.RELEVANCE.value:
        parameter.field = "score"

    # sort descending for DESCENDING and RELEVANCE
    reverse = parameter.order != models.SortOrder.ASCENDING

    if len(sorts) > 0:
        # if there are more sorting parameters, recurse to nest the sorts
        sorted_list = multi_column_sort(sorted_list, sorts)

    if parameter.field in ("_id", "score"):
        return sorted(
            sorted_list, key=lambda result: result[parameter.field], reverse=reverse
        )
    else:
        # the only top-level fields are "_id" and "score" -- all else is in "content"
        return sorted(
            sorted_list,
            key=lambda result: result["content"][parameter.field],
            reverse=reverse,
        )


def sorted_reference_results(
    joint_fixture: JointFixture,
    *,
    query: str,
    sorts: list[models.SortingParameter] | None = None,
    filters: list[models.Filter] | None = None,
) -> list[str]:
    """Used to independently retrieve and sort results by relevance and then id"""
    if not sorts:
        sorts = [RELEVANCE_SORT, ID_ASC]

    results = joint_fixture.mongodb.client[joint_fixture.config.db_name][
        CLASS_NAME
    ].find({"$text": {"$search": query}}, {"score": {"$meta": "textScore"}})
    results = [x for x in results]  # type: ignore

    for f in filters or []:
        # the only top-level fields are "_id" and "score" -- all else is in "content"
        if f.key in ("_id", "score"):
            results = [x for x in results if x[f.key] == f.value]  # type: ignore
        else:
            results = [x for x in results if x["content"][f.key] == f.value]  # type: ignore

    sorted_results = multi_column_sort(results, sorts)  # type: ignore

    return [result["_id"] for result in sorted_results]


async def test_happy_relevance(joint_fixture: JointFixture):
    """Make sure default works as expected"""
    query = "test"
    params: QueryParams = {"class_name": CLASS_NAME, "query": query}

    results = await joint_fixture.call_search_endpoint(params)
    assert results.count == 5

    reference_ids = sorted_reference_results(
        joint_fixture,
        query=query,
    )

    assert [hit.id_ for hit in results.hits] == reference_ids


async def test_happy_relevance_descending_id(joint_fixture: JointFixture):
    """Make sure default Pydantic model parameter works as expected"""
    query = "test"
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "query": query,
        "order_by": ["query", "id_"],
        "sort": ["relevance", "descending"],
    }

    results = await joint_fixture.call_search_endpoint(params)
    assert results.count == 5

    reference_ids = sorted_reference_results(
        joint_fixture, query=query, sorts=[RELEVANCE_SORT, ID_DESC]
    )

    assert [hit.id_ for hit in results.hits] == reference_ids


async def test_with_absent_term(joint_fixture: JointFixture):
    """Make sure nothing is pulled back with an absent term (sanity check)"""
    params: QueryParams = {"class_name": CLASS_NAME, "query": "doesnotexistinourtests"}

    results = await joint_fixture.call_search_endpoint(params)

    assert results.count == 0


async def test_limited_term(joint_fixture: JointFixture):
    """Make sure only results with the term are retrieved"""
    query = "alternative"
    params: QueryParams = {"class_name": CLASS_NAME, "query": query}

    results = await joint_fixture.call_search_endpoint(params)

    assert results.count == 2
    reference_ids = sorted_reference_results(joint_fixture, query=query)

    assert [hit.id_ for hit in results.hits] == reference_ids


async def test_two_words(joint_fixture: JointFixture):
    """Test with two different terms that appear in different fields"""
    query = "alternative test"
    params: QueryParams = {"class_name": CLASS_NAME, "query": query}

    results = await joint_fixture.call_search_endpoint(params)

    assert results.count == 5
    reference_ids = sorted_reference_results(joint_fixture, query=query)

    assert [hit.id_ for hit in results.hits] == reference_ids


async def test_with_filters(joint_fixture: JointFixture):
    """Test with filters applied but no sorting parameters"""
    query = "test"
    filters = [models.Filter(key="field", value="some data")]
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "query": query,
        "filter_by": [f.key for f in filters],
        "value": [f.value for f in filters],
    }

    results = await joint_fixture.call_search_endpoint(params)

    assert results.count == 1
    reference_ids = sorted_reference_results(
        joint_fixture, query=query, filters=filters
    )

    assert [hit.id_ for hit in results.hits] == reference_ids


async def test_with_filters_and_sorts(joint_fixture: JointFixture):
    """Test with filters applied and at least one sorting parameter (not relevance)"""
    query = "test"
    filters = [models.Filter(key="data", value="test test test test test")]
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "query": query,
        "filter_by": [f.key for f in filters],
        "value": [f.value for f in filters],
        "order_by": ["field", "id_"],
        "sort": ["ascending", "descending"],
    }

    results = await joint_fixture.call_search_endpoint(params)

    assert results.count == 2
    reference_ids = sorted_reference_results(
        joint_fixture,
        query=query,
        filters=filters,
        sorts=[FIELD_ASC, ID_DESC],
    )

    assert [hit.id_ for hit in results.hits] == reference_ids
