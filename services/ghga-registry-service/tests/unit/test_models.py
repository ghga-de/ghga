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

import pytest
from pydantic import BaseModel, ValidationError

from rs.core.models import PID


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


def test_pid_non_ascii():
    """A string containing non-ASCII characters is rejected."""
    with pytest.raises(ValidationError):
        _PIDModel(value="GHGA-STUDY-\u00fc01")  # ü is non-ASCII
