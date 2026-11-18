# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
    sort: list[str] | None = None,
    complete_resources: list[models.Resource] | None = None,
) -> list[models.Resource]:
    """Sort resources by all specified fields.

    This function simulates the sorting that is expected to be done by the database.
    Each entry of `sort` is a field name, prefixed with "-" for descending order.
    Since there's no spot for a top-level text score parameter in the resource model,
    the relevance tests need to use a slightly different version of this function.

    In the case that some of the sorted fields are not part of the resources, the
    complete resources which contain these missing fields must be passed as well.
    """
    order_by = [spec.removeprefix("-") for spec in sort or []]
    descending = [spec.startswith("-") for spec in sort or []]
    if "id_" not in order_by:
        # implicitly add id_ at the end since we also do it in the query handler
        order_by.append("id_")
        descending.append(False)

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
        for field, field_descending in zip(order_by, descending, strict=True):
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
            if field_descending:
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
    assert results.total_count > 0
    expected = sorted_resources(results.items)
    assert results.items == expected


@pytest.mark.parametrize("reverse", [False, True], ids=["normal", "reversed"])
async def test_sort_with_id_not_last(joint_fixture: JointFixture, reverse: bool):
    """Test sorting parameters that contain id_, but not as the final sorting field.

    Since we modify sorting parameters based on presence of id_, make sure there aren't
    any bugs that will break the sort or query process.
    """
    sort = ["-id_", "field"] if reverse else ["id_", "-field"]
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "query": "",
        "filters": [],
        "sort": ",".join(sort),
    }

    results = await joint_fixture.call_search_endpoint(params)
    assert results.items == sorted_resources(results.items, sort)


@pytest.mark.parametrize("reverse", [False, True], ids=["normal", "reversed"])
async def test_sort_with_params_but_not_id(joint_fixture: JointFixture, reverse: bool):
    """Test supplying sorting parameters but omitting id_.

    In order to provide consistent sorting, id_ should always be included. If it's not
    explicitly included, it will be added as the final sorting field in order to break
    any tie between otherwise equivalent keys. If it is included but is not the final
    field, then we should not modify the parameters.
    """
    sort = ["-field" if reverse else "field"]
    params: QueryParams = {"class_name": CLASS_NAME, "sort": ",".join(sort)}

    results = await joint_fixture.call_search_endpoint(params)
    assert results.items == sorted_resources(results.items, sort)


async def test_sort_with_multiple_fields(joint_fixture: JointFixture):
    """Test sorting by several fields with mixed directions."""
    sort = ["-field", "id_"]
    params: QueryParams = {"class_name": CLASS_NAME, "sort": " -field , id_ "}

    results = await joint_fixture.call_search_endpoint(params)
    assert results.items == sorted_resources(results.items, sort)


async def test_sort_with_invalid_field(joint_fixture: JointFixture):
    """Test supplying an invalid field name as a sort field.

    MongoDB treats any documents without a given sort field as if they had a `null`
    value for it. If we sort with a truly invalid field, it should have no impact on the
    resulting sort order.
    """
    params: QueryParams = {"class_name": CLASS_NAME, "sort": "some_bogus_field"}

    results = await joint_fixture.call_search_endpoint(params)
    assert results.items == sorted_resources(results.items)


@pytest.mark.parametrize("sort", ["field,field", "field,-field", "-field,field"])
async def test_sort_with_duplicate_field(joint_fixture: JointFixture, sort: str):
    """Supply a sort specification with two instances of the same sort field."""
    params: QueryParams = {"class_name": CLASS_NAME, "sort": sort}

    response = await joint_fixture.rest_client.get(url="/search", params=params)
    assert response.status_code == 422
    assert response.json()["detail"] == "Fields to sort by must be unique"


@pytest.mark.parametrize(
    "sort, field",
    [
        (",", ""),
        ("field,", ""),
        ("-", ""),
        ("field,-,id_", ""),
        ("$field", "$field"),
        ("-field.$sub", "field.$sub"),
        ("field.", "field."),
        ("field..sub", "field..sub"),
    ],
)
async def test_sort_with_malformed_field(
    joint_fixture: JointFixture, sort: str, field: str
):
    """Supply a sort specification with a field name that MongoDB cannot sort by."""
    params: QueryParams = {"class_name": CLASS_NAME, "sort": sort}

    response = await joint_fixture.rest_client.get(url="/search", params=params)
    assert response.status_code == 422
    assert response.json()["detail"] == f"Cannot sort by field '{field}'"


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

    sort = [f"-{field}" if reverse else field]
    params: QueryParams = {"class_name": class_name, "sort": ",".join(sort)}

    results = await joint_fixture.call_search_endpoint(params)
    assert results.items == sorted_resources(results.items, sort)


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

    sort = [f"-{field}" if reverse else field]
    params: QueryParams = {"class_name": class_name, "sort": ",".join(sort)}

    results = await joint_fixture.call_search_endpoint(params)

    # make sure the field is not returned in the results
    for resource in results.items:
        assert field not in resource.content

    # therefore, we cannot just sort the results,
    # but we need to fetch the field from the complete original resources
    complete_resources = joint_fixture.resources[class_name]
    assert results.items == sorted_resources(results.items, sort, complete_resources)
