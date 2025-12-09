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

"""Validation rules for the user registry service."""

import phonenumbers

__all__ = ["InvalidPhoneNumberError", "validate_phone_number"]


class InvalidPhoneNumberError(ValueError):
    """Indicates that a phone number is invalid."""

    def __init__(self, *, value: str) -> None:
        super().__init__(f"Invalid phone number: {value}")


def validate_phone_number(value: str, region: str | None = None) -> str:
    """Validate and normalize a phone number.

    By default, no default region is set, forcing an explicit international prefix.

    If the phone number is valid, it is returned in canonical E.164 format.
    If the phone number is invalid, an InvalidPhoneNumberError is raised.
    """
    try:
        number = phonenumbers.parse(value, region)
    except phonenumbers.NumberParseException as error:
        raise InvalidPhoneNumberError(value=value) from error

    if not phonenumbers.is_possible_number(number) or not phonenumbers.is_valid_number(
        number
    ):
        raise InvalidPhoneNumberError(value=value)

    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
