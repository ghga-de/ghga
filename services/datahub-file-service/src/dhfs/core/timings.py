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

"""Wrapper functionality for timing the processing of file parts"""

import time
from collections.abc import Generator
from contextlib import contextmanager

STAGES = ("download", "decrypt", "reencrypt", "verify", "digest", "fold", "upload")


class PartTimings:
    """Container for the time spent processing the parts of one file.

    Parts run concurrently, so the stage times, summed over all parts, can add up
    to more than the wall time.
    """

    def __init__(self):
        self.stages: dict[str, float] = dict.fromkeys(STAGES, 0.0)
        self.wall_time = 0.0

    @contextmanager
    def measure_stage(self, stage: str) -> Generator[None]:
        """Add the block's elapsed time to the given stage.

        Deliberately not exception-safe: a stage that raised did not do its work, so
        its time is not recorded.
        """
        start = time.monotonic()
        yield
        self.stages[stage] += time.monotonic() - start

    @contextmanager
    def measure_wall_time(self) -> Generator[None]:
        """Record the block's elapsed time as the wall time."""
        start = time.monotonic()
        yield
        self.wall_time = time.monotonic() - start

    @property
    def stage_total(self) -> float:
        """The stage times added up, which counts concurrent parts separately."""
        return sum(self.stages.values())

    @property
    def stage_seconds(self) -> dict[str, float]:
        """The stage times in seconds, rounded to milliseconds for reporting."""
        return {stage: round(elapsed, 3) for stage, elapsed in self.stages.items()}

    @property
    def wall_time_seconds(self) -> float:
        """The wall time in seconds, rounded to milliseconds for reporting."""
        return round(self.wall_time, 3)
