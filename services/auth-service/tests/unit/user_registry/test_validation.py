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

"""Test the validation functions for the user registry service."""

import pytest

from auth_service.user_registry.core.validation import (
    InvalidPhoneNumberError,
    validate_phone_number,
)


def test_invalid_number_format():
    """Test that phone numbers with invalid characters or format are rejected."""
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("foo bar")
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("++123456abc")
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("+49 0221/4710?123")


def test_impossible_number():
    """Test that properly formatted phone numbers which are impossible are rejected."""
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("+1 415 5")  # too short
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("+49 30 123456789012345")  # too long


def test_possible_but_invalid_number():
    """Test that possible but invalid numbers are rejected."""
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("+1 999 123 4567")
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("+49 123456 7890")


def test_valid_international_number():
    """Test that a valid international phone number is accepted and normalized."""
    assert validate_phone_number("+1 (415) 555-6789") == "+14155556789"
    assert validate_phone_number("+49 0221/4710-123") == "+492214710123"


def test_missing_international_prefix():
    """Test that a number missing the international prefix is rejected."""
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("(415) 555-6789")
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("0221/4710-123")


def test_invalid_international_prefix():
    """Test that phone numbers with invalid international prefixes are rejected."""
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("+99 12345678")
    with pytest.raises(InvalidPhoneNumberError):
        validate_phone_number("+1234 567890")
