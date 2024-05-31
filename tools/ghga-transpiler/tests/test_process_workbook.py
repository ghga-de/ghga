# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
"""Unit tests for core functions"""

import pytest
import semver

from ghga_transpiler.core import GHGAWorkbook, InvalidSematicVersion

from .fixtures.utils import create_workbook


def test_extract_good_version() -> None:
    """Function to check if the version extraction correctly gets workbook
    version from _properties worksheet
    """
    workbook = create_workbook("__properties")
    value = workbook["__properties"].cell(row=1, column=1, value="10.3.1-rc2").value
    # pylint: disable=protected-access
    version = GHGAWorkbook._get_version(workbook)
    assert version == semver.Version.parse(str(value))


def test_extract_bad_version() -> None:
    """Function to check if the version extraction correctly fails when an non
    semver string is specified in the _properties worksheet
    """
    workbook = create_workbook("__properties")
    workbook["__properties"].cell(row=1, column=1, value="20.10.3.1")

    with pytest.raises(InvalidSematicVersion):
        # pylint: disable=protected-access
        GHGAWorkbook._get_version(workbook)
