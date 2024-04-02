# Copyright 2024 Kersten Henrik Breuer
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

"""Test the freeze function."""

import pytest
from arcticfreeze import freeze

from tests.cases import INVALID_CASES, VALID_CASES, InvalidTestCase, ValidTestCase


@pytest.mark.parametrize(
    "test_case",
    VALID_CASES,
    ids=lambda test_case: test_case.name,
)
def test_valid_inputs(test_case: ValidTestCase):
    """Test the arctic freeze function with valid inputs."""
    assert freeze(test_case.inputs) == test_case.expected_outputs


@pytest.mark.parametrize(
    "test_case",
    INVALID_CASES,
    ids=lambda test_case: test_case.name,
)
def test_invalid_inputs(test_case: InvalidTestCase):
    """Test the arctic freeze function with invalid inputs."""
    with pytest.raises(test_case.expected_exception_type):
        freeze(test_case.inputs)
