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

"""Test the normalize module."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from schemapack import denormalize, load_datapack, load_schemapack
from schemapack._internals.spec.custom_types import EmbeddingProfile
from schemapack.exceptions import CircularRelationError
from schemapack.utils import read_json_or_yaml_mapping
from tests.fixtures.examples import (
    DENORMALIZED_CUSTOM_EMBEDDING_PATHS,
    DENORMALIZED_DEEP_EMBEDDING_PATHS,
    VALID_DATAPACK_PATHS,
    VALID_SCHEMAPACK_PATHS,
)


def run_denormalization_test(
    name: str,
    expected_denormalized_path: Path,
    embedding_profile: Mapping[str, Any] | None = None,
):
    """Run the denormalization test with optional ignored relations."""
    schemapack_name = name.split(".")[0]
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS[schemapack_name])
    datapack = load_datapack(VALID_DATAPACK_PATHS[name])
    expected_denormalized = read_json_or_yaml_mapping(expected_denormalized_path)
    denormalized = (
        denormalize(
            datapack=datapack,
            schemapack=schemapack,
            embedding_profile=embedding_profile,
        )
        if embedding_profile
        else denormalize(datapack=datapack, schemapack=schemapack)
    )

    assert denormalized == expected_denormalized


@pytest.mark.parametrize(
    "name, expected_denormalized_path",
    DENORMALIZED_DEEP_EMBEDDING_PATHS.items(),
    ids=DENORMALIZED_DEEP_EMBEDDING_PATHS.keys(),
)
def test_denormalize_deep_embedding(name: str, expected_denormalized_path: Path):
    """Test the denormalize function with valid datapacks."""
    run_denormalization_test(name, expected_denormalized_path)


EMBEDDING_PROFILE: Mapping[str, EmbeddingProfile] = {
    "simple_nested_relations": {
        "b": {"c": False}
    },  # direct relation c is not defined but embedded by default
    "rooted_simple_resources": {"files": False},
    "rooted_circular_relations": {"some_relation": {"some_relation": False}},
    "rooted_nested_relations": {
        "some_relation": {}
    },  # this is equivalent of profile {}
    "team_rooted_self_relation": {
        "teammates": {"teammates": False, "manager": False},
        "manager": True,
    },
}


@pytest.mark.parametrize(
    "name, expected_denormalized_path",
    DENORMALIZED_CUSTOM_EMBEDDING_PATHS.items(),
    ids=DENORMALIZED_CUSTOM_EMBEDDING_PATHS.keys(),
)
def test_denormalize_custom_embedding(name: str, expected_denormalized_path: Path):
    """Test the denormalize function with valid datapacks."""
    ignored_relations = EMBEDDING_PROFILE.get(name.split(".")[-1])
    run_denormalization_test(name, expected_denormalized_path, ignored_relations)


@pytest.mark.parametrize(
    "name",
    [
        "self_relation_rooted.rooted_circular_relations",
        "self_relation_rooted.rooted_circular_self_relations",
        "team_rooted.team_rooted_self_relation",
    ],
)
def test_denormalize_circular_relation(name: str):
    """Test the denormalize function fails on datapacks with circular relations."""
    schemapack_name = name.split(".")[0]
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS[schemapack_name])
    datapack = load_datapack(VALID_DATAPACK_PATHS[name])

    with pytest.raises(CircularRelationError):
        _ = denormalize(datapack=datapack, schemapack=schemapack)
