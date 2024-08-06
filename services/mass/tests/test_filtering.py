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
"""Tests concerning the filtering functionality"""

import pytest

from tests.fixtures.joint import JointFixture, QueryParams

CLASS_NAME = "FilteringTests"


@pytest.mark.asyncio
async def test_facets(joint_fixture: JointFixture):
    """Test that the facets are returned properly"""
    params: QueryParams = {"class_name": CLASS_NAME}

    results = await joint_fixture.call_search_endpoint(params)

    facets = results.facets
    assert len(facets) == 2

    facet = facets[0]
    assert facet.key == "species"
    assert facet.name == "Species"
    options = {option.value: option.count for option in facet.options}
    assert options == {"cat": 1, "dog": 2, "dolphin": 1, "monkey": 1}

    facet = facets[1]
    assert facet.key == "eats"
    assert facet.name == "Food"
    options = {option.value: option.count for option in facet.options}
    assert options == {
        "bananas": 1,
        "dog food": 1,
        "fish": 2,
        "lasagna": 1,
        "meatballs": 2,
        "shrimp": 1,
        "spaghetti": 2,
        "treats": 2,
    }


@pytest.mark.parametrize(
    "species,names",
    [("mouse", []), ("cat", ["Garfield"]), ("dog", ["Bruiser", "Lady"])],
    ids=[0, 1, 2],
)
@pytest.mark.asyncio
async def test_single_valued_with_with_single_filter(
    species: str, names: list[str], joint_fixture: JointFixture
):
    """Test that we can filter a single-valued field using a single value"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": "species",
        "value": species,
    }

    results = await joint_fixture.call_search_endpoint(params)

    # Check that the expected names are returned
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == names

    # Check that the facet only contains the filtered values
    facets = results.facets
    assert len(facets) == 2
    facet = facets[0]
    assert facet.key == "species"
    assert facet.name == "Species"
    options = facet.options
    if names:
        assert len(options) == 1
        option = options[0]
        assert option.count == len(names)
        assert option.value == species
    else:
        assert not options


@pytest.mark.parametrize(
    "food,names",
    [("broccoli", []), ("bananas", ["Jack"]), ("fish", ["Garfield", "Flipper"])],
    ids=[0, 1, 2],
)
@pytest.mark.asyncio
async def test_multi_valued_with_with_single_filter(
    food: str, names: list[str], joint_fixture: JointFixture
):
    """Test that we can filter a multi-valued field using a single value"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": "eats",
        "value": food,
    }

    results = await joint_fixture.call_search_endpoint(params)

    # Check that the expected names are returned
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == names

    # Check that the facet only contains the filtered values
    facets = results.facets
    assert len(facets) == 2
    facet = facets[1]
    assert facet.key == "eats"
    assert facet.name == "Food"
    options = facet.options
    if names:
        values = {option.value: option.count for option in options}
        if food == "fish":
            # should get everything that Garfield or Flipper eat
            assert values == {
                "fish": 2,
                "lasagna": 1,
                "meatballs": 1,
                "shrimp": 1,
                "spaghetti": 1,
                "treats": 1,
            }
        else:
            assert values == {food: 1}
    else:
        assert not options


@pytest.mark.asyncio
async def test_multiple_filters(joint_fixture: JointFixture):
    """Test the combination of multiple filters.

    Check that we use AND for different fields, but OR for the same fields.
    """
    # Query cats, dogs or monkeys that eat fish or bananas
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": ["species", "species", "species", "eats", "eats"],
        "value": ["cat", "dog", "monkey", "fish", "bananas"],
    }

    results = await joint_fixture.call_search_endpoint(params)

    # Only Jack and Garfield fulfill these conditions
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == ["Jack", "Garfield"]
