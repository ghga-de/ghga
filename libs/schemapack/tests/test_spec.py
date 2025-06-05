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

"""Tests the models module."""

import json

from immutabledict import immutabledict

from schemapack import load_schemapack
from schemapack._internals.load import load_datapack
from schemapack._internals.utils import read_json_or_yaml_mapping
from schemapack.spec.datapack import (
    SUPPORTED_DATA_PACK_VERSIONS,
    DataPack,
)
from tests.fixtures.examples import VALID_DATAPACK_PATHS, VALID_SCHEMAPACK_PATHS


def test_schemapack_is_hashable():
    """Test that instances of SchemaPack are hashable."""
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["simple_relations"])
    _ = hash(schemapack)


def test_comparison_and_hashing():
    """Test that equivalent schemapack (content schemas embedded or not) have the same
    hash and are equal.
    """
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["simple_relations"])
    schemapack_condensed = load_schemapack(
        VALID_SCHEMAPACK_PATHS["simple_relations_condensed"]
    )

    assert hash(schemapack) == hash(schemapack_condensed)
    assert schemapack == schemapack_condensed


def test_comparison_and_hashing_different():
    """Test that different SchemaPack instances have different hashes and are unequal."""
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["simple_relations"])

    schemapack_modified = schemapack.model_copy(
        update={
            "classes": immutabledict(
                {
                    "AdditionalClass": schemapack.classes[
                        set(schemapack.classes).pop()
                    ],
                    **schemapack.classes,
                }
            )
        }
    )

    assert hash(schemapack) != hash(schemapack_modified)
    assert schemapack != schemapack_modified


def test_content_schema_serialization():
    """Test that content schemas of a schemapack are serialized as dicts."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations_condensed"]
    schemapack = load_schemapack(schemapack_path)
    expected_schemapack_dict = read_json_or_yaml_mapping(schemapack_path)

    serialized_schemapack = json.loads(schemapack.model_dump_json())

    for class_name in schemapack.classes:
        assert (
            serialized_schemapack["classes"][class_name]["content"]
            == expected_schemapack_dict["classes"][class_name]["content"]
        )


def test_datapack_is_hashable():
    """Test that instances of DataPack are hashable."""
    datapack = load_datapack(VALID_DATAPACK_PATHS["simple_relations.simple_resources"])
    _ = hash(datapack)


def test_datapack_target_id_ordering_upon_dump():
    """Test that target_ids of a resource relation are sorted (i.e. the output is
    predictable) when serializing a datapack.
    """
    unsorted_target_ids = ["c", "a", "b"]
    sorted_target_ids = sorted(unsorted_target_ids)

    datapack = DataPack.model_validate(
        {
            "datapack": SUPPORTED_DATA_PACK_VERSIONS[-1],
            "resources": {
                "TestClass": {
                    "test_resource": {
                        "content": {},
                        "relations": {
                            "test_relations": {
                                "targetClass": "SomeClass",
                                "targetResources": unsorted_target_ids,
                            }
                        },
                    }
                },
                "SomeClass": {
                    "a": {"content": {}, "relations": {}},
                    "b": {"content": {}, "relations": {}},
                    "c": {"content": {}, "relations": {}},
                },
            },
        }
    )

    serialize_datapack = json.loads(datapack.model_dump_json())

    assert (
        serialize_datapack["resources"]["TestClass"]["test_resource"]["relations"][
            "test_relations"
        ]["targetResources"]
        == sorted_target_ids
    )
