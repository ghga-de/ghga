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

from pathlib import Path

import pytest

from schemapack.isolate import isolate
from schemapack.load import load_datapack, load_schemapack
from schemapack.spec.datapack import ClassName, ResourceId
from tests.fixtures.examples import VALID_DATAPACK_PATHS, VALID_SCHEMAPACK_PATHS


@pytest.mark.parametrize(
    "schemapack_path, non_rooted_datapack_path, resource_class, resource_id, rooted_datapack_path",
    [
        (
            VALID_SCHEMAPACK_PATHS["self_relation"],
            VALID_DATAPACK_PATHS["self_relation.multiple_relation_groups"],
            "SomeClass",
            "a",
            VALID_DATAPACK_PATHS["self_relation.rooted_nested_relations"],
        ),
        (
            VALID_SCHEMAPACK_PATHS["simple_relations"],
            VALID_DATAPACK_PATHS["simple_relations.non_rooted"],
            "Dataset",
            "example_dataset_1",
            VALID_DATAPACK_PATHS["simple_relations.rooted"],
        ),
        (
            VALID_SCHEMAPACK_PATHS["self_relation"],
            VALID_DATAPACK_PATHS["self_relation.circular_relations"],
            "SomeClass",
            "a",
            VALID_DATAPACK_PATHS["self_relation.rooted_circular_relations"],
        ),
        (
            VALID_SCHEMAPACK_PATHS["self_relation"],
            VALID_DATAPACK_PATHS["self_relation.circular_self_relations"],
            "SomeClass",
            "a",
            VALID_DATAPACK_PATHS["self_relation.rooted_circular_self_relations"],
        ),
    ],
    ids=[
        "nested_relations",
        "cross_class_relations",
        "circular_relations",
        "circular_self_relations",
    ],
)
def test_isolate(
    schemapack_path: Path,
    non_rooted_datapack_path: Path,
    resource_class: ClassName,
    resource_id: ResourceId,
    rooted_datapack_path: Path,
):
    """Test the isolate function."""
    schemapack = load_schemapack(schemapack_path)
    non_rooted_datapack = load_datapack(non_rooted_datapack_path)
    expected_rooted_datapack = load_datapack(rooted_datapack_path)

    rooted_datapack = isolate(
        datapack=non_rooted_datapack,
        class_name=resource_class,
        resource_id=resource_id,
        schemapack=schemapack,
    )

    assert rooted_datapack == expected_rooted_datapack
