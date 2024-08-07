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
"""Tests concerning the sorting functionality"""

import pytest

from mass.core import models
from tests.fixtures.joint import JointFixture, QueryParams

pytestmark = pytest.mark.asyncio()

CLASS_NAME = "SortingTests"


def sorted_resources(  # noqa: C901
    resources: list[models.Resource],
    order_by: list[str] | None = None,
    sort: list[str] | None = None,
    complete_resources: list[models.Resource] | None = None,
) -> list[models.Resource]:
    """Sort resources by all specified fields.

    This function simulates the sorting that is expected to be done by the database.
    Since there's no spot for a top-level text score parameter in the resource model,
    the relevance tests need to use a slightly different version of this function.

    In the case that some of the sorted fields are not part of the resources, the
    complete resources which contain these missing fields must be passed as well.
    """
    if order_by is None:
        order_by = []
    if sort is None:
        sort = []
    assert len(order_by) == len(sort)
    if "id_" not in order_by:
        # implicitly add id_ at the end since we also do it in the query handler
        order_by.append("id_")
        sort.append("ascending")

    def sort_key(resource: models.Resource) -> tuple:
        """Create a tuple that can be used as key for sorting the resource."""
        if complete_resources:
            for complete_resource in complete_resources:
                if complete_resource.id_ == resource.id_:
                    resource = complete_resource
                    break
            else:
                assert False, f"{resource.id_} not found in complete resources"
        key = []
        for field, field_sort in zip(order_by, sort, strict=True):
            resource_dict = resource.model_dump()
            if field != "id_":
                # the only top-level fields is "_id" -- all else is in "content"
                resource_dict = resource_dict["content"]
            # support dotted access
            sub_fields = field.split(".")
            sub_fields, field = sub_fields[:-1], sub_fields[-1]
            for sub_field in sub_fields:
                resource_dict = resource_dict.get(sub_field, {})
            value = resource_dict.get(field)
            # MongoDB returns nulls first, help Python to sort it properly
            key_for_null = value is not None
            if field_sort == "descending":
                key_for_null = not key_for_null
                if isinstance(value, str):
                    value = tuple(-ord(c) for c in value)
                elif isinstance(value, int | float):
                    value = -value
            key.append((key_for_null, value))
        return tuple(key)

    # sort the reversed resources to not rely on the already given order
    return sorted(reversed(resources), key=sort_key)


async def test_api_without_sort_parameters(joint_fixture: JointFixture):
    """Make sure default Pydantic model parameter works as expected"""
    params: QueryParams = {"class_name": CLASS_NAME}

    results = await joint_fixture.call_search_endpoint(params)
    assert results.count > 0
    expected = sorted_resources(results.hits)
    assert results.hits == expected


@pytest.mark.parametrize("reverse", [False, True], ids=["normal", "reversed"])
async def test_sort_with_id_not_last(joint_fixture: JointFixture, reverse: bool):
    """Test sorting parameters that contain id_, but not as the final sorting field.

    Since we modify sorting parameters based on presence of id_, make sure there aren't
    any bugs that will break the sort or query process.
    """
    order_by = ["id_", "field"]
    sort = ["ascending", "descending"]
    if reverse:
        sort.reverse()
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "order_by": order_by,
        "sort": sort,
    }

    results = await joint_fixture.call_search_endpoint(params)
    assert results.hits == sorted_resources(results.hits, order_by, sort)


@pytest.mark.parametrize("reverse", [False, True], ids=["normal", "reversed"])
async def test_sort_with_params_but_not_id(joint_fixture: JointFixture, reverse: bool):
    """Test supplying sorting parameters but omitting id_.

    In order to provide consistent sorting, id_ should always be included. If it's not
    explicitly included, it will be added as the final sorting field in order to break
    any tie between otherwise equivalent keys. If it is included but is not the final
    field, then we should not modify the parameters.
    """
    order_by = ["field"]
    sort = ["descending" if reverse else "ascending"]
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "order_by": order_by,
        "sort": sort,
    }

    results = await joint_fixture.call_search_endpoint(params)
    assert results.hits == sorted_resources(results.hits, order_by, sort)


async def test_sort_with_invalid_field(joint_fixture: JointFixture):
    """Test supplying an invalid field name as a sort field.

    MongoDB treats any documents without a given sort field as if they had a `null`
    value for it. If we sort with a truly invalid field, it should have no impact on the
    resulting sort order.
    """
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "order_by": ["some_bogus_field"],
        "sort": ["ascending"],
    }

    results = await joint_fixture.call_search_endpoint(params)
    assert results.hits == sorted_resources(results.hits)


@pytest.mark.parametrize("order", [-7, 17, "some_string"])
async def test_sort_with_invalid_sort_order(
    joint_fixture: JointFixture, order: str | int
):
    """Test supplying an invalid value for the sort order"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "order_by": ["field"],
        "sort": [order],  # type: ignore
    }

    response = await joint_fixture.rest_client.get(url="/search", params=params)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Input should be 'ascending', 'descending' or 'relevance'" in str(detail)


async def test_sort_with_invalid_field_and_sort_order(joint_fixture: JointFixture):
    """Test with both invalid field name and invalid sort order."""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "order_by": ["some_bogus_field"],
        "sort": ["also_bogus"],
    }

    response = await joint_fixture.rest_client.get(url="/search", params=params)
    assert response.status_code == 422


async def test_sort_with_duplicate_field(joint_fixture: JointFixture):
    """Supply sorting parameters with two instances of the same sort field.

    This should be prevented by the pydantic model validator and raise an HTTP error.
    """
    params = {
        "class_name": CLASS_NAME,
        "order_by": ["field", "field"],
        "sort": [models.SortOrder.ASCENDING.value, models.SortOrder.DESCENDING.value],
    }

    response = await joint_fixture.rest_client.get(url="/search", params=params)
    assert response.status_code == 422
    assert response.json()["detail"] == "Fields to order by must be unique"


async def test_sort_with_missing_sort(joint_fixture: JointFixture):
    """Supply sorting parameters with missing sort option.

    This should be prevented by the pydantic model validator and raise an HTTP error.
    """
    params = {
        "class_name": CLASS_NAME,
        "order_by": ["field"],
    }

    response = await joint_fixture.rest_client.get(url="/search", params=params)
    assert response.status_code == 422
    details = response.json()["detail"]
    assert details == "Number of fields to order by must match number of sort options"


async def test_sort_with_superfluous_sort(joint_fixture: JointFixture):
    """Supply sorting parameters with superfluous sort option.

    This should be prevented by the pydantic model validator and raise an HTTP error.
    """
    params = {
        "class_name": CLASS_NAME,
        "order_by": ["field"],
        "sort": [models.SortOrder.ASCENDING.value, models.SortOrder.DESCENDING.value],
    }

    response = await joint_fixture.rest_client.get(url="/search", params=params)
    assert response.status_code == 422
    details = response.json()["detail"]
    assert details == "Number of fields to order by must match number of sort options"


@pytest.mark.parametrize("reverse", [False, True], ids=["normal", "reversed"])
@pytest.mark.parametrize("field", ["type", "object.type"])
async def test_sort_with_one_of_the_selected_fields(
    joint_fixture: JointFixture, reverse: bool, field: str
):
    """Test sorting when fields are selected and one of them is used for sorting."""
    class_name = "NestedData"
    selected = joint_fixture.config.searchable_classes[class_name].selected_fields
    assert selected  # this resource has selected fields
    assert any(f.key == field for f in selected)  # field is selected

    order_by = [field]
    sort = ["descending" if reverse else "ascending"]
    params: QueryParams = {
        "class_name": class_name,
        "order_by": order_by,
        "sort": sort,
    }

    results = await joint_fixture.call_search_endpoint(params)
    assert results.hits == sorted_resources(results.hits, order_by, sort)


@pytest.mark.parametrize("reverse", [False, True], ids=["normal", "reversed"])
@pytest.mark.parametrize("field", ["category", "city"])
async def test_sort_with_one_of_the_unselected_fields(
    joint_fixture: JointFixture, reverse: bool, field: str
):
    """Test sorting when fields are selected but sorted by an unselected field."""
    class_name = "NestedData"
    selected = joint_fixture.config.searchable_classes[class_name].selected_fields
    assert selected  # this resource has selected fields
    assert not any(f.key == field for f in selected)  # field is unselected

    order_by = [field]
    sort = ["descending" if reverse else "ascending"]
    params: QueryParams = {
        "class_name": class_name,
        "order_by": order_by,
        "sort": sort,
    }

    results = await joint_fixture.call_search_endpoint(params)

    # make sure the field is not returned in the results
    for resource in results.hits:
        assert field not in resource.content

    # therefore, we cannot just sort the results,
    # but we need to fetch the field from the complete original resources
    complete_resources = joint_fixture.resources[class_name]
    assert results.hits == sorted_resources(
        results.hits, order_by, sort, complete_resources
    )
