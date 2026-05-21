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

"""Unit tests for Config validators"""

import pytest
from pydantic import ValidationError

from tests_fis.fixtures.config import get_config


@pytest.mark.parametrize(
    "specifier",
    [
        ">=1.0.0,<2.0.0",
        "~=2.0",
        "==1.*",
        ">=1.0",
        "!=1.5.0",
    ],
)
def test_dhfs_version_constraint_valid(specifier: str):
    """Valid PEP 440 specifiers should be accepted without error."""
    config = get_config(dhfs_version_constraint=specifier)
    assert config.dhfs_version_constraint == specifier


@pytest.mark.parametrize(
    "specifier",
    [
        "not-a-specifier",
        ">>1.0.0",
        "1.0.0",  # bare version without operator is invalid as a specifier
    ],
)
def test_dhfs_version_constraint_invalid(specifier: str):
    """Invalid PEP 440 specifiers should raise a ValidationError at config load time."""
    with pytest.raises(ValidationError):
        get_config(dhfs_version_constraint=specifier)
