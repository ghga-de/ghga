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

"""Tests for the race condition retry helper"""

import logging
from typing import Any

import pytest

from hexkit.protocols.dao import PreconditionFailedError, ResourceNotFoundError
from ucs.core._rc_helper import race_condition_retries

pytestmark = pytest.mark.asyncio()


class GaveUpError(RuntimeError):
    """Passed as `error_on_failure` to `race_condition_retries` in tests."""


class ConflictingUpdate:
    """An update that loses a race condition on its first `conflicts` tries."""

    def __init__(self, *, conflicts: int):
        self.conflicts = conflicts
        self.tries = 0

    async def run(self, **retry_kwargs: Any) -> None:
        """Run the update with `race_condition_retries`."""
        async for attempt in race_condition_retries(
            description="update the resource",
            error_on_failure=GaveUpError(),
            **retry_kwargs,
        ):
            with attempt:
                self.tries += 1
                if self.tries <= self.conflicts:
                    raise PreconditionFailedError(
                        id_="test", precondition={"try": self.tries}
                    )


@pytest.fixture()
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace the `sleep` used by `race_condition_retries` with one that only records
    the requested waits.
    """
    waits: list[float] = []

    async def record_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr("ucs.core._rc_helper.sleep", record_sleep)
    return waits


@pytest.mark.parametrize("conflicts", [0, 1, 2])
async def test_race_condition_retries_until_success(
    conflicts: int, sleeps: list[float]
):
    """Test that the action is retried after each conflict until it succeeds, waiting
    between `interval` and `interval + jitter` seconds each time.
    """
    update = ConflictingUpdate(conflicts=conflicts)
    await update.run(max_tries=3, interval=0.5, jitter=0.3)

    assert update.tries == conflicts + 1
    assert len(sleeps) == conflicts
    assert all(0.5 <= wait <= 0.8 for wait in sleeps)


async def test_race_condition_retries_exhausted(
    sleeps: list[float], caplog: pytest.LogCaptureFixture
):
    """Test that `error_on_failure` is raised after the last try, chained from the
    `PreconditionFailedError`, without waiting after that try.
    """
    logger_name = "ucs.tests.race_condition_retries"
    caplog.set_level(logging.DEBUG, logger=logger_name)
    update = ConflictingUpdate(conflicts=5)

    with pytest.raises(GaveUpError) as exc_info:
        await update.run(max_tries=3, logger=logging.getLogger(logger_name))

    assert update.tries == 3
    assert len(sleeps) == 2
    assert isinstance(exc_info.value.__cause__, PreconditionFailedError)
    assert [record.levelname for record in caplog.records] == [
        "DEBUG",
        "DEBUG",
        "DEBUG",
        "ERROR",
    ]
    assert "Failed 3 times to update the resource" in caplog.records[-1].getMessage()


@pytest.mark.parametrize("max_tries", [0, -1])
async def test_race_condition_retries_tries_at_least_once(
    max_tries: int, sleeps: list[float]
):
    """Test that the action is tried once when `max_tries` is below 1."""
    update = ConflictingUpdate(conflicts=1)

    with pytest.raises(GaveUpError):
        await update.run(max_tries=max_tries)

    assert update.tries == 1
    assert not sleeps


async def test_race_condition_retries_return_ends_retries():
    """Test that a `return` inside the block ends the retries."""

    async def update_if_changed() -> str:
        async for attempt in race_condition_retries(
            description="update the resource", error_on_failure=GaveUpError()
        ):
            with attempt:
                return "unchanged"
        return "retries ended without a return"

    assert await update_if_changed() == "unchanged"


async def test_race_condition_retries_other_errors():
    """Test that errors other than `PreconditionFailedError` are raised without a retry."""
    tries = 0

    with pytest.raises(ResourceNotFoundError):
        async for attempt in race_condition_retries(
            description="update the resource", error_on_failure=GaveUpError()
        ):
            with attempt:
                tries += 1
                raise ResourceNotFoundError(id_="test")

    assert tries == 1
