# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the validation module."""

from contextlib import nullcontext

import pytest

from ghga_service_commons.httpyexpect.validation import (
    ValidationError,
    assert_error_code,
    validate_exception_id,
)


@pytest.mark.parametrize(
    "status_code, is_valid",
    [
        (400, True),
        (403, True),
        (500, True),
        (599, True),
        (100, False),
        (200, False),
        (300, False),
        (600, False),
        (-100, False),
        ("100", False),
    ],
)
def test_check_status_code(status_code: object, is_valid: bool):
    """Test the `check_status_code` function."""

    with nullcontext() if is_valid else pytest.raises(ValidationError):  # type: ignore
        assert_error_code(status_code)


@pytest.mark.parametrize(
    "exception_id, is_valid",
    [
        ("myTestException123", True),
        ("myTeßtException", False),
        ("1myTestException", False),
        ("mt", False),
        ("TestExceptionWithABitMoreThan40Characters", False),
    ],
)
def test_check_exception_id(exception_id: object, is_valid: bool):
    """Test the `check_exception_id` function."""

    with nullcontext() if is_valid else pytest.raises(ValidationError):  # type: ignore
        validate_exception_id(exception_id)


def test_check_exception_id_status_code():
    """Test the `check_exception_id` function used with the status code argument."""
    status_code = 432

    with pytest.raises(ValidationError) as error:
        validate_exception_id("123myInvalidExceptionId", status_code=status_code)

    # Make sure the status code is mentioned in the error message:
    assert str(status_code) in str(error.value)
