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
"""Tests concerning the filtering functionality"""

import pytest

from tests.fixtures.joint import JointFixture, QueryParams

pytestmark = pytest.mark.asyncio()

CLASS_NAME = "FilteringTests"


async def test_facets(joint_fixture: JointFixture):
    """Test that the facets are returned properly"""
    params: QueryParams = {"class_name": CLASS_NAME}

    results = await joint_fixture.call_search_endpoint(params)

    facets = results.facets
    assert len(facets) == 6

    facet = facets[0]
    assert facet.key == "species"
    assert facet.name == "Species"
    options = {option.value: option.count for option in facet.options}
    assert options == {"cat": 1, "dog": 2, "dolphin": 1, "monkey": 1}
    assert list(options) == sorted(options)

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
    assert list(options) == sorted(options)

    facet = facets[2]
    assert facet.key == "friends.name"
    assert facet.name == "Friend"
    options = {option.value: option.count for option in facet.options}
    assert options == {
        "Arlene": 1,
        "Buddy": 1,
        "Elle": 1,
        "Hector": 1,
        "Jack": 3,
        "Jog": 1,
        "Jon": 2,
        "Odie": 1,
        "Paulette": 1,
        "Peter": 1,
        "Sandy": 1,
        "Tramp": 1,
        "Trusty": 1,
    }
    assert list(options) == sorted(options)

    facet = facets[3]
    assert facet.key == "items.type"
    assert facet.name == "Item"
    options = {option.value: option.count for option in facet.options}
    assert options == {
        "bowl": 3,  # only three animals have bowls
        "coin": 1,
        "collar": 2,  # only two animals wear collars
        "pistol": 1,
        "shirt": 3,
    }
    assert list(options) == sorted(options)

    facet = facets[4]
    assert facet.key == "items.color"
    assert facet.name == "Item color"
    options = {option.value: option.count for option in facet.options}
    assert options == {
        "blue": 1,
        "brown": 1,
        "gold": 2,
        "green": 1,
        "pink": 1,  # only one animal has a pink item
        "red": 2,  # but two animals have a red item
        "silver": 1,
        "white": 2,
        "yellow": 1,
    }
    assert list(options) == sorted(options)

    facet = facets[5]
    assert facet.key == "special.features.fur.color"
    assert facet.name == "Fur color"
    options = {option.value: option.count for option in facet.options}
    assert options == {
        "black": 1,
        "brown": 2,
        "cream": 1,
        "gray": 1,
        "light brown": 1,
        "orange": 1,
    }
    assert list(options) == sorted(options)


@pytest.mark.parametrize(
    "species,names",
    [("mouse", []), ("cat", ["Garfield"]), ("dog", ["Bruiser", "Lady"])],
    ids=range(1, 4),
)
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
    assert len(facets) == 6
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
    ids=range(1, 4),
)
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
    assert len(facets) == 6
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


async def test_multiple_filters(joint_fixture: JointFixture):
    """Test the combination of multiple filters.

    Check that we use AND for different fields, but OR for the same fields.
    """
    # Query cats, dogs or monkeys that eat fish or bananas
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": ["species"] * 3 + ["eats"] * 2,
        "value": ["cat", "dog", "monkey", "fish", "bananas"],
    }

    results = await joint_fixture.call_search_endpoint(params)

    # Only Jack and Garfield fulfill these conditions
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == ["Jack", "Garfield"]


@pytest.mark.parametrize(
    "friend,names",
    [
        ("Oscar", []),
        ("Paulette", ["Bruiser"]),
        ("Jon", ["Garfield", "Flipper"]),
        ("Jack", ["Jack", "Bruiser", "Garfield"]),
    ],
    ids=range(1, 5),
)
async def test_filter_for_common_friend(
    friend: str, names: list[str], joint_fixture: JointFixture
):
    """Test that we can search for animals with a common friend"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": "friends.name",
        "value": friend,
    }

    results = await joint_fixture.call_search_endpoint(params)

    # Check that the expected names are returned
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == names

    # Check that the facet contains the friend in question
    facets = results.facets
    assert len(facets) == 6
    facet = facets[2]
    assert facet.key == "friends.name"
    assert facet.name == "Friend"
    if names:
        assert any(option.value == friend for option in facet.options)


async def test_filter_for_couple_of_friends(joint_fixture: JointFixture):
    """Test that we can search for animals with one of the specified friends"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": ["friends.name"] * 3,
        "value": ["Hector", "Sandy", "Tramp"],
    }

    results = await joint_fixture.call_search_endpoint(params)

    # only Jack, Lady and Flipper have Hector, Sandy or Tramp as friend
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == ["Jack", "Lady", "Flipper"]

    # Check that the facet contains the selected friends and all their co-friends
    facets = results.facets
    assert len(facets) == 6
    facet = facets[2]
    assert facet.key == "friends.name"
    assert facet.name == "Friend"
    option_values = [option.value for option in facet.options]
    co_friends = "Buddy Hector Jack Jog Jon Peter Sandy Tramp Trusty".split()
    assert option_values == co_friends
    assert all(option.count == 1 for option in facet.options)


async def test_filter_animals_with_collars(joint_fixture: JointFixture):
    """Test that we can search for animals wearing collars"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": "items.type",
        "value": "collar",
    }

    results = await joint_fixture.call_search_endpoint(params)

    # only Bruiser and Lady wear collars, Garfield does not
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == ["Bruiser", "Lady"]

    # Check that the facet also has their other items
    facets = results.facets
    assert len(facets) == 6
    facet = facets[3]
    assert facet.name == "Item"
    option_values = [option.value for option in facet.options]
    assert option_values == ["bowl", "collar", "shirt"]
    assert all(option.count == 2 for option in facet.options)

    # Check the colors of all of their items
    facet = facets[4]
    assert facet.name == "Item color"
    option_values = [option.value for option in facet.options]
    print(facet.options)
    assert option_values == ["blue", "brown", "gold", "green", "pink", "white"]
    assert all(option.count == 1 for option in facet.options)

    # Check that we also see what these two like to eat
    facet = facets[1]
    assert facet.name == "Food"
    option_values = [option.value for option in facet.options]
    assert option_values == ["dog food", "meatballs", "spaghetti", "treats"]
    assert all(option.count == 1 for option in facet.options)


async def test_filter_animals_with_collars_or_pistols(joint_fixture: JointFixture):
    """Test that we can search for animals with collars or pistols"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": ["items.type"] * 2,
        "value": ["collar", "pistol"],
    }

    results = await joint_fixture.call_search_endpoint(params)

    # only Bruiser and Lady wear collars, only Jack has a pistol
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == ["Jack", "Bruiser", "Lady"]


@pytest.mark.parametrize(
    "color,names",
    [
        ("green", []),
        ("orange", ["Garfield"]),
        ("brown", ["Jack", "Lady"]),
    ],
    ids=range(1, 4),
)
async def test_filter_for_fur_color(
    color: str, names: list[str], joint_fixture: JointFixture
):
    """Test that we can search for animals with a given fur color"""
    params: QueryParams = {
        "class_name": CLASS_NAME,
        "filter_by": "special.features.fur.color",
        "value": color,
    }

    results = await joint_fixture.call_search_endpoint(params)

    # Check that the expected names are returned
    returned_names = [resource.content["name"] for resource in results.hits]
    assert returned_names == names

    # Check that the facet contains the color in question
    facets = results.facets
    assert len(facets) == 6
    facet = facets[5]
    assert facet.key == "special.features.fur.color"
    assert facet.name == "Fur color"
    if names:
        assert any(option.value == color for option in facet.options)
