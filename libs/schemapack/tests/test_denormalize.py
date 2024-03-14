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

"""Test the normalize module."""

from pathlib import Path

import pytest

from schemapack import denormalize, load_datapack, load_schemapack
from schemapack.exceptions import CircularRelationError
from schemapack.utils import read_json_or_yaml_mapping
from tests.fixtures.examples import (
    DENORMALIZED_PATHS,
    VALID_DATAPACK_PATHS,
    VALID_SCHEMAPACK_PATHS,
)


@pytest.mark.parametrize(
    "name, expected_denomalizated_path",
    DENORMALIZED_PATHS.items(),
    ids=DENORMALIZED_PATHS.keys(),
)
def test_denormalize(name: str, expected_denomalizated_path: Path):
    """Test the denormalize function with valid datapacks."""
    schemapack_name = name.split(".")[0]
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS[schemapack_name])
    datapack = load_datapack(VALID_DATAPACK_PATHS[name])
    expected_denomalizated = read_json_or_yaml_mapping(expected_denomalizated_path)

    denomalizated = denormalize(datapack=datapack, schemapack=schemapack)

    assert denomalizated == expected_denomalizated


@pytest.mark.parametrize(
    "name",
    [
        "self_relation_rooted.rooted_circular_relations",
        "self_relation_rooted.rooted_circular_self_relations",
    ],
)
def test_denormalize_circular_relation(name: str):
    """Test the denormalize function fails on datapacks with circular relations."""
    schemapack_name = name.split(".")[0]
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS[schemapack_name])
    datapack = load_datapack(VALID_DATAPACK_PATHS[name])

    with pytest.raises(CircularRelationError):
        _ = denormalize(datapack=datapack, schemapack=schemapack)
