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

"""Test the utils.accessions module."""

import pytest
from pydantic import TypeAdapter, ValidationError

from ghga_service_commons.utils.accessions import DatasetAccession, FileAccession


@pytest.mark.parametrize(
    "accession",
    ["GHGAD12345678901234", "GHGA.26.ABC.1.DS.XYZ"],
)
def test_good_dataset_accession(accession: str):
    """Test that legacy and new dataset accessions are accepted."""
    assert TypeAdapter(DatasetAccession).validate_python(accession) == accession


@pytest.mark.parametrize(
    "accession",
    [
        "hello",
        "GHGA.26",
        "GHGA.26.ABC.1",
        "GHGA.26.ABC.1.sample_a",
        "GHGA.26.AB1.1.DS.XYZ",
        "GHGA.2026.ABC.1.DS.XYZ",
        "GHGA.26.ABC.0.DS.XYZ",
        "GHGA.26.ABC.01.DS.XYZ",
        "GHGA.٢٦.ABC.١.DS.XYZ",
        "EGA.26.ABC.1.DS.XYZ",
        "GHGA.26.AB.1.DS.XYZ",
        "GHGA.26.ABCD.1.DS.XYZ",
        "GHGA.26.ABC.1.DX.XYZ",
        "GHGA.26.ABC.1.DS.XY",
        "GHGA.26.ABC.1.DS.XYZW",
    ],
)
def test_bad_dataset_accession(accession: str):
    """Test that study PIDs, other entities' accessions and malformed ones are rejected."""
    with pytest.raises(ValidationError):
        TypeAdapter(DatasetAccession).validate_python(accession)


@pytest.mark.parametrize(
    "accession",
    ["GHGAF01", "GHGA.26.ABC.1.file_a", "GHGA.26.ABC.12.file-b"],
)
def test_good_file_accession(accession: str):
    """Test that legacy and study PID file accessions are accepted."""
    assert TypeAdapter(FileAccession).validate_python(accession) == accession


@pytest.mark.parametrize(
    "accession",
    [
        "some_file_id",
        "GHGA.26.ABC.1",
        "GHGA.26.AB1.1.file_a",
        "GHGA.2026.ABC.1.f",
        "GHGA.26.ABC.12.some.file",
        "GHGA.26.ABC.1.File_A",
        "GHGA.26.ABC.1.DS.XYZ",
        "EGA.26.ABC.1.file_a",
        "GHGA.26.ABCD.1.file_a",
        "GHGA.26.ABC.0.file_a",
        "GHGA.26.ABC.01.file_a",
        "GHGA.٢٦.ABC.١.file_a",
    ],
)
def test_bad_file_accession(accession: str):
    """Test that dataset PIDs, unnormalized aliases and malformed accessions are
    rejected.
    """
    with pytest.raises(ValidationError):
        TypeAdapter(FileAccession).validate_python(accession)
