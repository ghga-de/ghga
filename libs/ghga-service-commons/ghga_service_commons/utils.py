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

"""General utilities that don't require heavy dependencies."""

from __future__ import annotations

from abc import ABC
from contextlib import contextmanager
from datetime import datetime, timezone
from tempfile import NamedTemporaryFile
from typing import Any, BinaryIO, Callable, Generator, cast

from pydantic import parse_obj_as

__all__ = [
    "DateTimeUTC",
    "UTC",
    "assert_tz_is_utc",
    "big_temp_file",
    "now_as_utc",
]

UTC = timezone.utc


class NamedBinaryIO(ABC, BinaryIO):
    """Return type of NamedTemporaryFile."""

    name: str


@contextmanager
def big_temp_file(size: int) -> Generator[NamedBinaryIO, None, None]:
    """Generates a big file with approximately the specified size in bytes."""
    current_size = 0
    current_number = 0
    next_number = 1
    with NamedTemporaryFile("w+b") as temp_file:
        while current_size <= size:
            byte_addition = f"{current_number}\n".encode("ASCII")
            current_size += len(byte_addition)
            temp_file.write(byte_addition)
            previous_number = current_number
            current_number = next_number
            next_number = previous_number + current_number
        temp_file.flush()
        yield cast(NamedBinaryIO, temp_file)


class DateTimeUTC(datetime):
    """A pydantic type for values that should have an UTC timezone.

    This behaves exactly like the normal datetime type, but requires that the value
    has a timezone and converts the timezone to UTC if necessary.
    """

    @classmethod
    def construct(cls, *args, **kwargs) -> DateTimeUTC:
        """Construct a datetime with UTC timezone."""
        if kwargs.get("tzinfo") is None:
            kwargs["tzinfo"] = UTC
        return cls(*args, **kwargs)

    @classmethod
    def __get_validators__(cls) -> Generator[Callable[[Any], datetime], None, None]:
        """Get all validators."""
        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> datetime:
        """Validate the given value."""
        date_value = parse_obj_as(datetime, value)
        if date_value.tzinfo is None:
            raise ValueError(f"Date-time value is missing a timezone: {value!r}")
        if date_value.tzinfo is not UTC:
            date_value = date_value.astimezone(UTC)
        return date_value


def assert_tz_is_utc() -> None:
    """Verifies that the default timezone is set to UTC.

    Raises a Runtimeerror if the default timezone is set differently.
    """
    if datetime.now().astimezone().tzinfo != UTC:
        raise RuntimeError("System must be configured to use UTC.")


def now_as_utc() -> DateTimeUTC:
    """Return the current datetime with UTC timezone.

    Note: This is different from datetime.utcnow() which has no timezone.
    """
    return DateTimeUTC.now(UTC)
