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

"""Test schemapack loading."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from schemapack.load import load_schemapack
from tests.fixtures.examples import INVALID_SCHEMAPACK_PATHS, VALID_SCHEMAPACK_PATHS


@pytest.mark.parametrize(
    "path", VALID_SCHEMAPACK_PATHS.values(), ids=VALID_SCHEMAPACK_PATHS
)
def test_load_schemapack_valid(path: Path):
    """Test loading valid schemapacks."""
    _ = load_schemapack(path)


@pytest.mark.parametrize(
    "name, path", INVALID_SCHEMAPACK_PATHS.items(), ids=INVALID_SCHEMAPACK_PATHS
)
def test_load_schemapack_invalid(name: str, path: Path):
    """Test loading invalid schemapacks."""
    error_type = name.split(".")[0]

    with pytest.raises(ValidationError) as error:
        _ = load_schemapack(path)

    original_errors = error.value.errors()
    assert len(original_errors) == 1

    assert original_errors[0]["type"] == error_type
