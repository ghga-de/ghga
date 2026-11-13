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
#

"""Unit tests for the validation and masking of phone numbers"""

import pytest

from ars.core.phone import mask_phone_number, validate_phone_number


@pytest.mark.parametrize(
    "phone",
    [
        "06221 424242",
        "+49 123",
        "not a number",
        "+1 555 0100 0100 0100",
        "+49 6221 42 4242",
        "+49 900 1234567",
    ],
)
def test_validate_invalid_phone_number(phone: str):
    """Test that invalid, unprefixed, landline and premium-rate numbers are rejected."""
    with pytest.raises(ValueError, match="Invalid phone number"):
        validate_phone_number(phone)


@pytest.mark.parametrize(
    "phone, normalized",
    [
        ("+49 1512 3456789", "+4915123456789"),
        ("+1 201 555 0123", "+12015550123"),
    ],
)
def test_validate_phone_number(phone: str, normalized: str):
    """Test that mobile numbers, and US numbers that may be mobile, are accepted."""
    assert validate_phone_number(phone) == normalized


@pytest.mark.parametrize(
    "phone, masked",
    [
        ("+4915123456789", "+49…6789"),
        ("+29022158", "+290…58"),
        ("+2902158", "+290…58"),
    ],
)
def test_mask_phone_number(phone: str, masked: str):
    """Test that at most half of the national number is shown."""
    assert mask_phone_number(phone) == masked
