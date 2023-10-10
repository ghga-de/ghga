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
"""Tests concerning the sorting functionality"""

import pytest
from hexkit.custom_types import JsonObject

from mass.core import models
from tests.fixtures.joint import JointFixture

CLASS_NAME = "SortingTests"
BASIC_SORT_PARAMETERS = [
    models.SortingParameter(field="id_", order=models.SortOrder.ASCENDING)
]


def multi_column_sort(
    resources: list[models.Resource], sorts: list[models.SortingParameter]
) -> list[models.Resource]:
    """This is equivalent to nested sorted() calls.

    This uses the same approach as the sorting function in test_relevance, but the
    difference is that this function uses Resource models and doesn't work with the
    relevance sorting parameter. There's no spot for a top-level text score parameter in
    the resource model, which is why the relevance tests use a slightly different version
    of this function.

    The sorting parameters are supplied in order of most significant to least significant,
    so we take them off the front and apply sorted(). If there are more parameters to
    apply (more sorts), we recurse until we apply the final parameter. The sorted lists
    are passed back up the call chain.
    """
    sorted_list = resources.copy()
    sorts = sorts.copy()

    parameter = sorts[0]
    del sorts[0]

    # sort descending for DESCENDING and RELEVANCE
    reverse = parameter.order != models.SortOrder.ASCENDING

    if len(sorts) > 0:
        # if there are more sorting parameters, recurse to nest the sorts
        sorted_list = multi_column_sort(sorted_list, sorts)

    if parameter.field == "id_":
        return sorted(
            sorted_list,
            key=lambda result: result.dict()[parameter.field],
            reverse=reverse,
        )
    else:
        # the only top-level fields is "_id" -- all else is in "content"
        return sorted(
            sorted_list,
            key=lambda result: result.dict()["content"][parameter.field],
            reverse=reverse,
        )


@pytest.mark.asyncio
async def test_api_without_sort_parameters(joint_fixture: JointFixture):
    """Make sure default Pydantic model parameter works as expected"""
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
    }

    results = await joint_fixture.call_search_endpoint(
        search_parameters=search_parameters
    )
    assert results.count > 0
    expected = multi_column_sort(results.hits, BASIC_SORT_PARAMETERS)
    assert results.hits == expected


@pytest.mark.asyncio
async def test_sort_with_id_not_last(joint_fixture: JointFixture):
    """Test sorting parameters that contain id_, but id_ is not final sorting field.

    Since we modify sorting parameters based on presence of id_, make sure there aren't
    any bugs that will break the sort or query process.
    """
    sorts = [
        {"field": "id_", "order": "ascending"},
        {"field": "field", "order": "descending"},
    ]
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": sorts,
    }

    sorts_in_model_form = [
        models.SortingParameter(
            field=param["field"], order=models.SortOrder(param["order"])
        )
        for param in sorts
    ]
    results = await joint_fixture.call_search_endpoint(search_parameters)
    assert results.hits == multi_column_sort(results.hits, sorts_in_model_form)


@pytest.mark.asyncio
async def test_sort_with_params_but_not_id(joint_fixture: JointFixture):
    """Test supplying sorting parameters but omitting id_.

    In order to provide consistent sorting, id_ should always be included. If it's not
    explicitly included, it will be added as the final sorting field in order to break
    any tie between otherwise equivalent keys. If it is included but is not the final
    field, then we should not modify the parameters.
    """
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [
            {"field": "field", "order": models.SortOrder.ASCENDING.value}
        ],
    }

    results = await joint_fixture.call_search_endpoint(search_parameters)
    assert results.hits == multi_column_sort(results.hits, BASIC_SORT_PARAMETERS)


@pytest.mark.asyncio
async def test_sort_with_invalid_field(joint_fixture: JointFixture):
    """Test supplying an invalid field name as a sort field.

    MongoDB treats any documents without a given sort field as if they had a `null`
    value for it. If we sort with a truly invalid field, it should have no impact on the
    resulting sort order.
    """
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [
            {
                "field": "some_bogus_field",
                "order": models.SortOrder.ASCENDING.value,
            }
        ],
    }

    results = await joint_fixture.call_search_endpoint(search_parameters)
    assert results.hits == multi_column_sort(results.hits, BASIC_SORT_PARAMETERS)


@pytest.mark.parametrize("order", [-7, 17, "some_string"])
@pytest.mark.asyncio
async def test_sort_with_invalid_sort_order(joint_fixture: JointFixture, order):
    """Test supplying an invalid value for the sort order"""
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [{"field": "field", "order": order}],
    }

    response = await joint_fixture.rest_client.post(
        url="/rpc/search", json=search_parameters
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sort_with_invalid_field_and_sort_order(joint_fixture: JointFixture):
    """Test with both invalid field name and invalid sort order."""
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [{"field": "some_bogus_field", "order": -7}],
    }

    response = await joint_fixture.rest_client.post(
        url="/rpc/search", json=search_parameters
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sort_with_duplicate_field(joint_fixture: JointFixture):
    """Supply sorting parameters with two instances of the same sort field.

    This should be prevented by the pydantic model validator and raise an HTTP error.
    """
    search_parameters: JsonObject = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sorting_parameters": [
            {"field": "field", "order": models.SortOrder.ASCENDING.value},
            {"field": "field", "order": models.SortOrder.DESCENDING.value},
        ],
    }
    response = await joint_fixture.rest_client.post(
        url="/rpc/search", json=search_parameters
    )
    assert response.status_code == 422
