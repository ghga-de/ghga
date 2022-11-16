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

"""Test the utils module for the user management service."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from pytest import mark, raises

from auth_service.user_management.utils import DateTimeUTC, now_as_utc


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
        datetime(2022, 11, 15, 12, 0, 0, tzinfo=timezone.utc),
        datetime.now(timezone.utc),
        datetime.fromtimestamp(0, timezone.utc),
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
    assert model.dt.tzinfo is not timezone.utc
    assert model.dt.utcoffset() != timedelta(0)
    assert model.du.tzinfo is timezone.utc
    assert model.du.utcoffset() == timedelta(0)

    assert model.dt == model.du


def test_now_as_utc():
    """Test the now_as_utc function."""
    assert isinstance(now_as_utc(), datetime)
    assert now_as_utc().tzinfo is timezone.utc
    assert abs(now_as_utc().timestamp() - datetime.now().timestamp()) < 5
