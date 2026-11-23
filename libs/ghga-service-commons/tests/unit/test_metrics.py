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

"""Tests for the gauge refresh helper."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any, cast

import pytest
from opentelemetry.metrics import CallbackOptions, Meter

from ghga_service_commons import metrics
from ghga_service_commons.metrics import refresh_gauge

pytestmark = pytest.mark.asyncio

INTERVAL = 0.01


class FakeMeter:
    """Keeps the callback of the one observable gauge created with it."""

    def __init__(self):
        self.created: dict[str, Any] = {}
        self._callback: Callable | None = None

    def create_observable_gauge(
        self, name: str, callbacks=None, unit: str = "", description: str = ""
    ):
        """Remember how the gauge was created and its callback."""
        self.created = {"name": name, "unit": unit, "description": description}
        (self._callback,) = callbacks

    def observe(self) -> list[float]:
        """Collect like the exporter thread does and return the reported values."""
        assert self._callback is not None
        return [o.value for o in self._callback(CallbackOptions())]


def new_meter() -> tuple[FakeMeter, Meter]:
    """Return a fake meter, both as itself and typed as a Meter for the helper."""
    meter = FakeMeter()
    return meter, cast(Meter, meter)


def counting_read() -> Callable:
    """Return an async read that yields 0, 1, 2, ... on successive calls."""
    counter = iter(range(1000))

    async def read() -> float:
        return next(counter)

    return read


async def test_reports_last_value_read():
    """The callback reports the latest value, which follows the refresh interval."""
    fake, meter = new_meter()

    async with refresh_gauge(
        name="test.items",
        description="Items.",
        unit="{item}",
        read=counting_read(),
        interval=INTERVAL,
        meter=meter,
    ):
        await asyncio.sleep(0)
        assert fake.observe() == [0]
        await asyncio.sleep(INTERVAL * 5)
        (later,) = fake.observe()

    assert later > 0
    assert fake.created == {
        "name": "test.items",
        "unit": "{item}",
        "description": "Items.",
    }


async def test_nothing_before_first_read():
    """Until a read has succeeded, the callback reports nothing."""
    fake, meter = new_meter()
    started = asyncio.Event()

    async def read() -> float:
        started.set()
        await asyncio.sleep(60)
        return 1

    async with refresh_gauge(
        name="test.items", description="Items.", read=read, meter=meter
    ):
        await started.wait()
        assert fake.observe() == []


async def test_failing_read_keeps_previous_value(caplog: pytest.LogCaptureFixture):
    """A failing call is logged, keeps the last value and does not stop the task."""
    fake, meter = new_meter()
    results: list[float | Exception] = [1, RuntimeError("database down")]

    async def read() -> float:
        result = results.pop(0) if results else 3
        if isinstance(result, Exception):
            raise result
        return result

    with caplog.at_level(logging.WARNING):
        async with refresh_gauge(
            name="test.items",
            description="Items.",
            read=read,
            interval=INTERVAL,
            meter=meter,
        ):
            await asyncio.sleep(0)
            assert fake.observe() == [1]
            await asyncio.sleep(INTERVAL * 5)
            assert fake.observe() == [3]

    assert "database down" in caplog.text


async def test_slow_read_times_out():
    """A call that exceeds the timeout is abandoned instead of stalling the task."""
    fake, meter = new_meter()
    calls = 0

    async def read() -> float:
        nonlocal calls
        calls += 1
        if calls == 1:
            await asyncio.sleep(60)
        return calls

    async with refresh_gauge(
        name="test.items",
        description="Items.",
        read=read,
        interval=INTERVAL,
        timeout=INTERVAL,
        meter=meter,
    ):
        await asyncio.sleep(INTERVAL * 6)
        (value,) = fake.observe()

    assert value > 1


async def test_stale_value_is_not_reported(monkeypatch: pytest.MonkeyPatch):
    """Once the last successful read is older than max_age, nothing is reported."""
    fake, meter = new_meter()
    now = 1000.0
    monkeypatch.setattr(metrics.time, "monotonic", lambda: now)

    async with refresh_gauge(
        name="test.items",
        description="Items.",
        read=counting_read(),
        interval=60,
        max_age=90,
        meter=meter,
    ):
        await asyncio.sleep(0)
        assert fake.observe() == [0]

        now += 90
        assert fake.observe() == [0]

        now += 1
        assert fake.observe() == []


async def test_silent_and_stopped_after_exit():
    """Leaving the context stops the task and silences the callback."""
    fake, meter = new_meter()

    async with refresh_gauge(
        name="test.items",
        description="Items.",
        read=counting_read(),
        interval=INTERVAL,
        meter=meter,
    ):
        await asyncio.sleep(0)
        assert fake.observe() == [0]

    assert fake.observe() == []
    names = [task.get_name() for task in asyncio.all_tasks()]
    assert "refresh_gauge:test.items" not in names
