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

"""Unit tests for the PartTimings class"""

import pytest

from dhfs.core import timings as timings_module
from dhfs.core.timings import STAGES, PartTimings


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace `time.monotonic()` with a clock that returns the queued values."""
    ticks: list[float] = []
    monkeypatch.setattr(timings_module.time, "monotonic", lambda: ticks.pop(0))
    return ticks


def test_stages_add_up_and_round(clock: list[float]):
    """Test that repeated measurements of a stage add up, and are rounded on output."""
    timings = PartTimings()
    clock.extend([0.0, 1.00011, 5.0, 7.0])
    with timings.measure_stage("upload"):
        pass
    with timings.measure_stage("upload"):
        pass

    assert set(timings.stage_seconds) == set(STAGES)
    assert timings.stage_seconds["upload"] == 3.0
    assert timings.stage_seconds["download"] == 0.0
    assert timings.stage_total == pytest.approx(3.00011)


def test_failed_stage_is_not_recorded(clock: list[float]):
    """Test that a stage that raised adds no time."""
    timings = PartTimings()
    clock.extend([0.0, 4.0])
    with pytest.raises(RuntimeError), timings.measure_stage("decrypt"):
        raise RuntimeError()

    assert timings.stages["decrypt"] == 0.0


def test_wall_time(clock: list[float]):
    """Test that the wall time is recorded and rounded to milliseconds."""
    timings = PartTimings()
    clock.extend([10.0, 12.34567])
    with timings.measure_wall_time():
        pass

    assert timings.wall_time_seconds == 2.346
