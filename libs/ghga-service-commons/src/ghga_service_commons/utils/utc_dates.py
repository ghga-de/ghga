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

"""Utilities for ensuring the consistent use of the UTC timezone."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import AwareDatetime, TypeAdapter
from pydantic.functional_validators import BeforeValidator

__all__ = ["UTCDatetime", "convert_tz_to_utc", "UTC", "assert_tz_is_utc", "now_as_utc"]

UTC = timezone.utc


def assert_tz_is_utc() -> None:
    """Verify that the default timezone is set to UTC.

    Raise a RuntimeError if the default timezone is set differently.
    """
    if datetime.now().astimezone().tzinfo != UTC:
        raise RuntimeError("System must be configured to use UTC.")


def convert_tz_to_utc(date: datetime) -> datetime:
    """Convert the timezone of the given datetime object to UTC."""
    return date.astimezone(UTC) if date.tzinfo is not UTC else date


# A Pydantic type for values that should have an UTC timezone.
# This behaves exactly like the normal datetime type, but requires a
# a timezone aware object which is converted to UTC if necessary.
# Validation and timezone conversion is only done via Pydantic.
# Direct use of UTCDatetime is identical to normal datetime.
UTCDatetime = Annotated[
    datetime,
    # note that BeforeValidators run right-to-left
    BeforeValidator(convert_tz_to_utc),
    BeforeValidator(TypeAdapter(AwareDatetime).validate_python),
]


def utc_datetime(*args, **kwargs) -> UTCDatetime:
    """Construct a datetime with UTC timezone."""
    if kwargs.get("tzinfo") is None:
        kwargs["tzinfo"] = UTC
    return UTCDatetime(*args, **kwargs)


def now_as_utc() -> UTCDatetime:
    """Return the current datetime with UTC timezone.

    Note: This is different from datetime.utcnow() which has no timezone.
    """
    return UTCDatetime.now(UTC)
