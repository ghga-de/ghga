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

"""Test the isolate module."""

import pytest

from schemapack import isolate, load_datapack, load_schemapack
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
        class_name=resource_class,
        resource_id=resource_id,
        schemapack=schemapack,
        datapack=datapack,
    )

    assert rooted_schemapack == expected_rooted_schemapack
    assert rooted_datapack == expected_rooted_datapack
