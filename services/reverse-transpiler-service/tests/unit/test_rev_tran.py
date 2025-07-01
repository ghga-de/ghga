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

"""Unit tests for the reverse transpiler class."""

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from rts.core.rev_tran import ReverseTranspiler, SheetNameConfig
from tests.fixtures.config import get_config


def test_missing_name_config():
    """Test that the reverse transpiler raises an error if no name is configured."""
    config = get_config()
    reverse_transpiler = ReverseTranspiler(
        config=config, metadata_dao=AsyncMock(), workbook_dao=AsyncMock()
    )
    with pytest.raises(ReverseTranspiler.SheetNamingError):
        reverse_transpiler._translate_sheet_name("some_sheet")


def test_too_long_sheet_name():
    """Test that configuring sheet names longer than 31 characters begets an error."""
    with pytest.raises(ValidationError):
        _ = SheetNameConfig(sheet_names={"test": "A long sheet name" * 10})
