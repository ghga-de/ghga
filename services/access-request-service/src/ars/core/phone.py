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

"""Validation of phone numbers"""

import phonenumbers

__all__ = ["mask_phone_number", "validate_phone_number"]


def validate_phone_number(value: str) -> str:
    """Validate a mobile phone number and return it in E.164 format.

    No default region is set, so the number needs an international prefix.
    Landlines are refused, since German networks no longer deliver SMS to them.
    Numbers that cannot be told apart from landlines, as in the US, pass.

    Raises a `ValueError` if the phone number is invalid or not a mobile number.
    """
    try:
        number = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException as error:
        raise ValueError(f"Invalid phone number: {value}") from error
    if not (
        phonenumbers.is_possible_number(number) and phonenumbers.is_valid_number(number)
    ):
        raise ValueError(f"Invalid phone number: {value}")
    if phonenumbers.number_type(number) not in (
        phonenumbers.PhoneNumberType.MOBILE,
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
    ):
        raise ValueError(f"Invalid phone number: {value} is not a mobile number")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def mask_phone_number(phone: str) -> str:
    """Mask all but the country prefix and the last digits of a phone number.

    Shows four digits, but at most half of the national number, so that a short
    number stays masked as well.

    Expects the phone number in E.164 format.
    """
    number = phonenumbers.parse(phone, None)
    prefix = f"+{number.country_code}"
    national = phone[len(prefix) :]
    shown = min(4, len(national) // 2)
    return prefix + "…" + national[len(national) - shown :]
