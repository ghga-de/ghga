# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the isolate module."""

import pytest

from schemapack import (
    exceptions,
    isolate,
    isolate_class,
    isolate_resource,
    load_datapack,
    load_schemapack,
)
from schemapack.spec.custom_types import ClassName, ResourceId
from tests.fixtures.examples import VALID_DATAPACK_PATHS, VALID_SCHEMAPACK_PATHS


@pytest.mark.parametrize(
    "datapack_name, resource_class, resource_id, rooted_datapack_name",
    [
        (
            "self_relation.multiple_relation_groups",
            "SomeClass",
            "a",
            "self_relation_rooted.rooted_nested_relations",
        ),
        (
            "simple_relations.simple_resources",
            "Dataset",
            "example_dataset_1",
            "simple_relations_rooted.rooted_simple_resources",
        ),
        (
            "self_relation.circular_relations",
            "SomeClass",
            "a",
            "self_relation_rooted.rooted_circular_relations",
        ),
        (
            "self_relation.circular_self_relations",
            "SomeClass",
            "a",
            "self_relation_rooted.rooted_circular_self_relations",
        ),
        (
            "complex_cardinality.all_cardinalities",
            "A",
            "a1",
            "complex_cardinality_rooted.rooted_all_cardinalities",
        ),
    ],
    ids=[
        "nested_relations",
        "cross_class_relations",
        "circular_relations",
        "circular_self_relations",
        "all_cardinalities",
    ],
)
def test_isolate(
    datapack_name: str,
    resource_class: ClassName,
    resource_id: ResourceId,
    rooted_datapack_name: str,
):
    """Test the isolate function."""
    datapack_path = VALID_DATAPACK_PATHS[datapack_name]
    expected_rooted_datapack_path = VALID_DATAPACK_PATHS[rooted_datapack_name]
    schemapack_name = datapack_name.split(".")[0]
    schemapack_path = VALID_SCHEMAPACK_PATHS[schemapack_name]
    rooted_schempack_name = rooted_datapack_name.split(".")[0]
    expected_rooted_schemapack_path = VALID_SCHEMAPACK_PATHS[rooted_schempack_name]

    datapack = load_datapack(datapack_path)
    expected_rooted_datapack = load_datapack(expected_rooted_datapack_path)
    schemapack = load_schemapack(schemapack_path)
    expected_rooted_schemapack = load_schemapack(expected_rooted_schemapack_path)

    rooted_schemapack, rooted_datapack = isolate(
        root_class_name=resource_class,
        root_resource_id=resource_id,
        schemapack=schemapack,
        datapack=datapack,
    )

    assert rooted_schemapack == expected_rooted_schemapack
    assert rooted_datapack == expected_rooted_datapack


def test_isolate_with_non_existing_class():
    """Test the isolate function with a non-existing class."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack_path = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]
    schemapack = load_schemapack(schemapack_path)
    datapack = load_datapack(datapack_path)

    with pytest.raises(exceptions.ClassNotFoundError) as error:
        isolate(
            root_class_name="NonExistingClass",
            root_resource_id="example_dataset_1",
            schemapack=schemapack,
            datapack=datapack,
        )
    assert "schemapack" in str(error)


def test_isolate_with_non_existing_resource():
    """Test the isolate function with a non-existing resource."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack_path = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]
    schemapack = load_schemapack(schemapack_path)
    datapack = load_datapack(datapack_path)

    with pytest.raises(exceptions.ResourceNotFoundError):
        isolate(
            root_class_name="Dataset",
            root_resource_id="NonExistingResource",
            schemapack=schemapack,
            datapack=datapack,
        )


def test_isolate_resource_non_exisiting_class():
    """Test the isolate_resource function with a non-existing class. Happy paths are
    tested as part of the isolate function and appear not worth repeating for this
    specific function.
    """
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack_path = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]
    schemapack = load_schemapack(schemapack_path)
    datapack = load_datapack(datapack_path)

    with pytest.raises(exceptions.ClassNotFoundError):
        isolate_resource(
            class_name="NonExistingClass",
            resource_id="example_dataset_1",
            schemapack=schemapack,
            datapack=datapack,
        )


def test_isolate_class_non_exisiting_class():
    """Test the isolate_class function with a non-existing class. Happy paths are
    tested as part of the isolate function and appear not worth repeating for this
    specific function.
    """
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    schemapack = load_schemapack(schemapack_path)

    with pytest.raises(exceptions.ClassNotFoundError):
        isolate_class(
            schemapack=schemapack,
            class_name="NonExistingClass",
        )


def test_isolate_class_downscoping():
    """Test that unrelated classes are not included in the isolated schemapack."""
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["unrelated_classes"])
    expected_schemapack = load_schemapack(
        VALID_SCHEMAPACK_PATHS["unrelated_classes_rooted"]
    )

    observed_schemapack = isolate_class(class_name="SomeClass", schemapack=schemapack)
    assert observed_schemapack == expected_schemapack
