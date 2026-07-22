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

"""Unit tests for core data models"""

from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from rs.core.models import PID, Study, StudyStatus


class _PIDModel(BaseModel):
    value: PID


def test_pid_valid_ascii():
    """A normal ASCII string is accepted."""
    assert _PIDModel(value="GHGA-STUDY-001").value == "GHGA-STUDY-001"


def test_pid_max_length_boundary():
    """A string of exactly 256 ASCII characters is accepted."""
    assert _PIDModel(value="x" * 256).value == "x" * 256


def test_pid_too_long():
    """A string exceeding 256 characters is rejected."""
    with pytest.raises(ValidationError):
        _PIDModel(value="x" * 257)


def _minimal_study(**kwargs) -> Study:
    """Create a Study with only the required fields set."""
    defaults = {
        "id": "GHGA-STUDY-001",
        "title": "A study",
        "description": "A detailed abstract",
        "types": ["whole_genome_sequencing"],
        "affiliations": ["UKT"],
        "status": StudyStatus.DRAFT,
        "created_by": uuid4(),
    }
    defaults.update(kwargs)
    return Study(**defaults)  # type: ignore


def test_study_status_values():
    """The StudyStatus enum has the expected string values."""
    assert StudyStatus.DRAFT == "draft"
    assert StudyStatus.ARCHIVED == "archived"


def test_study_defaults():
    """Optional and computed fields default as expected for a fresh draft."""
    study = _minimal_study()
    assert study.status is StudyStatus.DRAFT
    assert study.approved is None
    assert study.approved_by is None
    assert study.superseded_by_id is None
    assert study.has_em is False
    assert study.num_datasets == 0
    assert study.num_publications == 0
    assert study.created is not None


def test_study_invalid_id_rejected():
    """A non-ASCII study id is rejected via the PID constraint."""
    with pytest.raises(ValidationError):
        _minimal_study(id="GHGA-STUDY-ü01")


def test_study_invalid_status_rejected():
    """An unknown status value is rejected."""
    with pytest.raises(ValidationError):
        _minimal_study(status="published")


def test_pid_non_ascii():
    """A string containing non-ASCII characters is rejected."""
    with pytest.raises(ValidationError):
        _PIDModel(value="GHGA-STUDY-\u00fc01")  # ü is non-ASCII
