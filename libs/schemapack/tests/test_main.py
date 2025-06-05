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

"""Tests the main module."""

from pathlib import Path

import pytest

from schemapack import load_and_validate
from schemapack.exceptions import (
    BaseError,
    DataPackSpecError,
    ParsingError,
    ValidationError,
)
from tests.fixtures.examples import (
    INVALID_DATAPACK_PATHS,
    VALID_DATAPACK_PATHS,
    VALID_SCHEMAPACK_PATHS,
)


@pytest.mark.parametrize(
    "name, path", VALID_DATAPACK_PATHS.items(), ids=VALID_DATAPACK_PATHS
)
def test_load_and_validate_valid(name: str, path: Path):
    """Test load_and_validate function with valid schemapack and valid datapacks."""
    schemapack_name = name.split(".", 1)[0]
    schemapack_path = VALID_SCHEMAPACK_PATHS[schemapack_name]

    _ = load_and_validate(schemapack_path=schemapack_path, datapack_path=path)


@pytest.mark.parametrize(
    "name, path", INVALID_DATAPACK_PATHS.items(), ids=INVALID_DATAPACK_PATHS
)
def test_load_and_validate_invalid(name: str, path: Path):
    """Test load_and_validate function with valid schemapack but invalid datapacks."""
    schemapack_name, error_type = name.split(".", 2)[:2]
    schemapack_path = VALID_SCHEMAPACK_PATHS[schemapack_name]
    with pytest.raises(BaseError) as exception_info:
        _ = load_and_validate(schemapack_path=schemapack_path, datapack_path=path)
    # Either a DataPackSpecError or ValidationError is expected:
    if error_type == "DataPackSpecError":
        assert isinstance(exception_info.value, DataPackSpecError)
    elif error_type == "ParsingError":
        assert isinstance(exception_info.value, ParsingError)
    else:
        assert isinstance(exception_info.value, ValidationError)
        error_records = exception_info.value.records
        assert len(error_records) == 1
        assert error_records[0].type == error_type
