# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Utilities for the user management package."""

from datetime import datetime, timezone

from pydantic import parse_obj_as

__all__ = ["DateTimeUTC", "now_as_utc"]


UTC = timezone.utc


class DateTimeUTC(datetime):
    """A pydantic type for values that should have an UTC timezone.

    This behaves exactly like the normal datetime type, but requires that the value
    has a timezone and converts the timezone to UTC if necessary.
    """

    @classmethod
    def create(cls, *args, **kwargs):
        """Create a datetime with UTC timezone."""
        if kwargs.get("tzinfo") is None:
            kwargs["tzinfo"] = UTC
        return cls(*args, **kwargs)

    @classmethod
    def __get_validators__(cls):
        """Get all validators."""
        yield cls.validate

    @classmethod
    def validate(cls, value):
        """Validate the given value."""
        date_value = parse_obj_as(datetime, value)
        if date_value.tzinfo is None:
            raise ValueError(f"Date-time value is missing a timezone: {value!r}")
        if date_value.tzinfo is not UTC:
            date_value = date_value.astimezone(UTC)
        return date_value


def now_as_utc():
    """Return the current datetime with UTC timezone.

    Note: This is different from datetime.utcnow() which has no timezone.
    """
    return datetime.now(UTC)
