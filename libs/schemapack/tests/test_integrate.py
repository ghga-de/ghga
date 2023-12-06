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

"""Test the integrate module."""

from pathlib import Path

import pytest

from schemapack.exceptions import CircularRelationError
from schemapack.integrate import integrate
from schemapack.load import load_datapack, load_schemapack
from schemapack.utils import read_json_or_yaml
from tests.fixtures.examples import (
    INTEGRATIONS_PATHS,
    VALID_DATAPACK_PATHS,
    VALID_SCHEMAPACK_PATHS,
)


@pytest.mark.parametrize(
    "name, expected_integration_path",
    INTEGRATIONS_PATHS.items(),
    ids=INTEGRATIONS_PATHS.keys(),
)
def test_integrate(name: str, expected_integration_path: Path):
    """Test the integrate function with valid datapacks."""
    schemapack_name = name.split(".")[0]
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS[schemapack_name])
    datapack = load_datapack(VALID_DATAPACK_PATHS[name])
    expected_integration = read_json_or_yaml(expected_integration_path)

    integration = integrate(datapack=datapack, schemapack=schemapack)

    assert integration == expected_integration


@pytest.mark.parametrize(
    "name",
    [
        "self_relation.rooted_circular_relations",
        "self_relation.rooted_circular_self_relations",
    ],
)
def test_integrate_circular_relation(name: str):
    """Test the integrate function fails on datapacks with circular relations."""
    schemapack_name = name.split(".")[0]
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS[schemapack_name])
    datapack = load_datapack(VALID_DATAPACK_PATHS[name])

    with pytest.raises(CircularRelationError):
        _ = integrate(datapack=datapack, schemapack=schemapack)
