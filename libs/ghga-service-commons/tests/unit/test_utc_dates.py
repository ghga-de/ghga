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

"""Test the utils.utc_dates module."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from pytest import mark, raises

from ghga_service_commons.utils.utc_dates import UTC, DateTimeUTC, now_as_utc


@mark.parametrize(
    "value",
    [
        "2022-11-15 12:00:00",
        "2022-11-15T12:00:00",
        datetime(2022, 11, 15, 12, 0, 0),
        datetime.now(),
        datetime.utcnow(),
        datetime.utcfromtimestamp(0),
    ],
)
def test_does_not_accept_naive_datetimes(value):
    """Test that DateTimeUTC does not accept naive datetimes."""

    class Model(BaseModel):
        """Test model"""

        d: DateTimeUTC

    with raises(ValueError, match="missing a timezone"):
        Model(d=value)


@mark.parametrize(
    "value",
    [
        "2022-11-15T12:00:00+00:00",
        "2022-11-15T12:00:00Z",
        datetime(2022, 11, 15, 12, 0, 0, tzinfo=UTC),
        datetime.now(timezone.utc),
        datetime.fromtimestamp(0, UTC),
    ],
)
def test_accept_aware_datetimes_in_utc(value):
    """Test that DateTimeUTC does not accepts timezone aware UTC datetimes."""

    class Model(BaseModel):
        """Test model"""

        dt: datetime
        du: DateTimeUTC

    model = Model(dt=value, du=value)

    assert model.dt == model.du


@mark.parametrize(
    "value",
    [
        "2022-11-15T12:00:00+03:00",
        "2022-11-15T12:00:00-03:00",
        datetime(2022, 11, 15, 12, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
        datetime.now(ZoneInfo("Asia/Tokyo")),
    ],
)
def test_converts_datetimes_to_utc(value):
    """Test that DateTimeUTC converts other time zones to UTC."""

    class Model(BaseModel):
        """Test model"""

        dt: datetime
        du: DateTimeUTC

    model = Model(dt=value, du=value)

    assert model.dt.tzinfo is not None
    assert model.dt.tzinfo is not UTC
    assert model.dt.utcoffset() != timedelta(0)
    assert model.du.tzinfo is UTC
    assert model.du.utcoffset() == timedelta(0)

    assert model.dt == model.du


def test_datetime_utc_constructor():
    """Test the constructor for DateTimeUTC values."""

    date = DateTimeUTC.construct(2022, 11, 15, 12, 0, 0)
    assert isinstance(date, DateTimeUTC)
    assert date.tzinfo is UTC
    assert date.utcoffset() == timedelta(0)

    date = DateTimeUTC.construct(2022, 11, 15, 12, 0, 0, tzinfo=UTC)
    assert isinstance(date, DateTimeUTC)
    assert date.tzinfo is UTC
    assert date.utcoffset() == timedelta(0)


def test_now_as_utc():
    """Test the now_as_utc function."""
    assert isinstance(now_as_utc(), DateTimeUTC)
    assert now_as_utc().tzinfo is UTC
    assert now_as_utc().utcoffset() == timedelta(0)
    assert abs(now_as_utc().timestamp() - datetime.now().timestamp()) < 5
