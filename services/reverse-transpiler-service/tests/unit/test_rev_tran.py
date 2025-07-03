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
from rts.models import StudyMetadata
from tests.fixtures.config import get_config


def test_sheet_naming():
    """Test that the reverse transpiler handles sheet names properly.

    If a name is configured, it should use that.
    If no name is configured, it should use the original but truncate it to 31
    characters if necessary, otherwise Excel will complain.
    """
    config = get_config()
    reverse_transpiler = ReverseTranspiler(
        config=config, metadata_dao=AsyncMock(), workbook_dao=AsyncMock()
    )
    # Configured
    assert reverse_transpiler._translate_sheet_name("analyses") == "Analysis"
    # Not configured but under 31 chars
    assert reverse_transpiler._translate_sheet_name("bald_knobber") == "bald_knobber"
    # Not configured, over 31 chars. Test truncation
    long_name = "this_is_a_very_long_name_if_you_are_excel"
    assert reverse_transpiler._translate_sheet_name(long_name) == long_name[:31]


def test_too_long_sheet_name():
    """Test that configuring sheet names longer than 31 characters begets an error."""
    with pytest.raises(ValidationError):
        _ = SheetNameConfig(sheet_names={"test": "A long sheet name" * 10})


def test_column_aggregation():
    """Test that we get the union of all column names across rows in a property.

    The test content will have two rows for "samples", each with a unique column.
    We expect to see both columns used in the output spreadsheet, not just 'col1'.
    """
    content = {
        "samples": [
            {"accession": "abc123", "alias": "sample1", "col1": "testval"},
            {"accession": "abc123", "alias": "sample1", "col2": "testval2"},
        ]
    }
    metadata = StudyMetadata(study_accession="my_study", content=content)

    # do the reverse transpilation
    config = get_config()
    reverse_transpiler = ReverseTranspiler(
        config=config, metadata_dao=AsyncMock(), workbook_dao=AsyncMock()
    )
    workbook = reverse_transpiler._reverse_transpile(study_metadata=metadata)

    # Check that col1 and col2 both exist
    sheet = workbook["Sample"]  # name translated by config
    header_cells: list[str] = [
        str(col[0])
        for col in sheet.iter_cols(
            min_col=1, max_col=4, min_row=1, max_row=1, values_only=True
        )
    ]
    assert sorted(header_cells) == ["accession", "alias", "col1", "col2"]
