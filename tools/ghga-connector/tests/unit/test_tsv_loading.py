# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Unit tests for load_file_info_from_tsv in batch_processing"""

from pathlib import Path

import pytest

from ghga_connector import exceptions
from ghga_connector.core.uploading.batch_processing import load_file_info_from_tsv


def _write_tsv(tmp_path: Path, lines: list[str]) -> Path:
    tsv_path = tmp_path / "files.tsv"
    tsv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tsv_path


def test_parses_path_then_alias(tmp_path):
    """The first column is the path and the second is the alias (ds-kit format)."""
    data_file = tmp_path / "sample.bam"
    data_file.write_bytes(b"hello")
    tsv_path = _write_tsv(tmp_path, [f"{data_file}\tmy-alias"])

    result = load_file_info_from_tsv(tsv_path)

    assert len(result) == 1
    assert result[0].alias == "my-alias"
    assert result[0].path == data_file.resolve()
    assert result[0].decrypted_size == 5


def test_ignores_blank_lines(tmp_path):
    """Blank lines in the TSV are skipped."""
    first = tmp_path / "a.bam"
    first.write_bytes(b"a")
    second = tmp_path / "b.bam"
    second.write_bytes(b"bb")
    tsv_path = _write_tsv(tmp_path, [f"{first}\talias-a", "", f"{second}\talias-b", ""])

    result = load_file_info_from_tsv(tsv_path)

    assert {fi.alias for fi in result} == {"alias-a", "alias-b"}


def test_extra_columns_are_ignored(tmp_path):
    """Only the first two columns (path, alias) are used; extra columns are ignored."""
    data_file = tmp_path / "a.bam"
    data_file.write_bytes(b"a")
    tsv_path = _write_tsv(tmp_path, [f"{data_file}\tthe-alias\tsomething-else"])

    result = load_file_info_from_tsv(tsv_path)

    assert len(result) == 1
    assert result[0].alias == "the-alias"


def test_no_tab_raises(tmp_path):
    """A line with no tab character raises a RuntimeError."""
    data_file = tmp_path / "a.bam"
    data_file.write_bytes(b"a")
    tsv_path = _write_tsv(tmp_path, [str(data_file)])

    with pytest.raises(RuntimeError, match="must be tab-separated"):
        load_file_info_from_tsv(tsv_path)


def test_space_separated_line_hints_at_spaces(tmp_path):
    """A space-separated line gets a targeted hint about using spaces, not tabs."""
    data_file = tmp_path / "a.bam"
    data_file.write_bytes(b"a")
    tsv_path = _write_tsv(tmp_path, [f"{data_file}    the-alias"])

    with pytest.raises(RuntimeError, match="separates the columns with spaces"):
        load_file_info_from_tsv(tsv_path)


def test_empty_alias_column_raises(tmp_path):
    """A line whose alias column is empty (between tabs) raises a RuntimeError."""
    data_file = tmp_path / "a.bam"
    data_file.write_bytes(b"a")
    tsv_path = _write_tsv(tmp_path, [f"{data_file}\t\textra"])

    with pytest.raises(RuntimeError, match="missing a file path or alias"):
        load_file_info_from_tsv(tsv_path)


def test_missing_tsv_raises(tmp_path):
    """A non-existent TSV path raises FileDoesNotExistError."""
    with pytest.raises(exceptions.FileDoesNotExistError):
        load_file_info_from_tsv(tmp_path / "nope.tsv")


def test_missing_referenced_file_raises(tmp_path):
    """A TSV referencing a file that does not exist raises FileDoesNotExistError."""
    tsv_path = _write_tsv(tmp_path, [f"{tmp_path / 'ghost.bam'}\tghost"])

    with pytest.raises(exceptions.FileDoesNotExistError):
        load_file_info_from_tsv(tsv_path)


def test_duplicate_alias_raises(tmp_path):
    """Duplicate aliases across rows raise a ValueError."""
    first = tmp_path / "a.bam"
    first.write_bytes(b"a")
    second = tmp_path / "b.bam"
    second.write_bytes(b"bb")
    tsv_path = _write_tsv(tmp_path, [f"{first}\tsame", f"{second}\tsame"])

    with pytest.raises(ValueError, match="Duplicate alias"):
        load_file_info_from_tsv(tsv_path)


def test_duplicate_path_raises(tmp_path):
    """The same file path under two aliases raises a ValueError."""
    data_file = tmp_path / "a.bam"
    data_file.write_bytes(b"a")
    tsv_path = _write_tsv(tmp_path, [f"{data_file}\tone", f"{data_file}\ttwo"])

    with pytest.raises(ValueError, match="Duplicate path"):
        load_file_info_from_tsv(tsv_path)


def test_empty_file_raises(tmp_path):
    """An empty TSV raises a RuntimeError."""
    tsv_path = tmp_path / "empty.tsv"
    tsv_path.write_text("\n\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="No file entries"):
        load_file_info_from_tsv(tsv_path)
