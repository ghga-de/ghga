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
from typing import Any, cast

import pytest
from opentelemetry.metrics import Meter

from ghga_service_commons.metrics import refresh_gauge

pytestmark = pytest.mark.asyncio

INTERVAL = 0.01


class FakeGauge:
    """Records every value it is set to."""

    def __init__(self):
        self.values: list[float] = []

    def set(self, amount: float, attributes: Any = None, context: Any = None) -> None:
        """Record the value."""
        self.values.append(amount)


class FakeMeter:
    """Hands out one FakeGauge and remembers how it was created."""

    def __init__(self):
        self.gauge = FakeGauge()
        self.created: dict[str, Any] = {}

    def create_gauge(self, name: str, unit: str = "", description: str = ""):
        """Return the fake gauge."""
        self.created = {"name": name, "unit": unit, "description": description}
        return self.gauge


def new_meter() -> tuple[FakeMeter, Meter]:
    """Return a fake meter, both as itself and typed as a Meter for the helper."""
    meter = FakeMeter()
    return meter, cast(Meter, meter)


async def test_gauge_is_set_on_entry_and_refreshed():
    """The first value is there on entry, and later values follow on the interval."""
    fake, meter = new_meter()
    counter = iter(range(100))

    async def read() -> float:
        return next(counter)

    async with refresh_gauge(
        name="test.items",
        description="Items.",
        unit="{item}",
        read=read,
        interval=INTERVAL,
        meter=meter,
    ):
        await asyncio.sleep(0)
        assert fake.gauge.values == [0]
        await asyncio.sleep(INTERVAL * 5)

    assert fake.created == {
        "name": "test.items",
        "unit": "{item}",
        "description": "Items.",
    }
    assert len(fake.gauge.values) > 1
    assert fake.gauge.values == sorted(fake.gauge.values)


async def test_failing_read_keeps_previous_value(caplog: pytest.LogCaptureFixture):
    """A failing call is logged, leaves the gauge alone and does not stop the task."""
    fake, meter = new_meter()
    results: list[float | Exception] = [1, RuntimeError("database down"), 3]

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
            await asyncio.sleep(INTERVAL * 5)

    assert fake.gauge.values[:2] == [1, 3]
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

    assert fake.gauge.values
    assert 1 not in fake.gauge.values


async def test_task_is_gone_after_exit():
    """Leaving the context cancels and awaits the refresh task."""
    _, meter = new_meter()

    async def read() -> float:
        return 1

    async with refresh_gauge(
        name="test.items",
        description="Items.",
        read=read,
        interval=INTERVAL,
        meter=meter,
    ):
        await asyncio.sleep(0)

    names = [task.get_name() for task in asyncio.all_tasks()]
    assert "refresh_gauge:test.items" not in names
