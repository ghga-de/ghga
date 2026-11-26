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

"""Unit tests for the interrogation loop in `run_interrogator()`."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from dhfs.main import run_interrogator
from dhfs.ports.outbound.interrogator import InterrogatorPort
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "concluded_a_file, waits",
    [(True, False), (False, True)],
    ids=["concluded_a_file", "inconclusive"],
)
async def test_wait_after_a_round(concluded_a_file: bool, waits: bool):
    """DHFS waits out the minimum run interval only after an inconclusive round."""
    interrogator = AsyncMock(spec=InterrogatorPort)
    # The CriticalError in the second round ends the loop
    interrogator.interrogate_new_files.side_effect = [
        concluded_a_file,
        InterrogatorPort.CriticalError("end the loop"),
    ]

    @asynccontextmanager
    async def prepare_mock_interrogator(*, config, claimant_id):
        yield interrogator

    sleep = AsyncMock()
    with (
        patch("dhfs.main.Config", get_config),
        patch("dhfs.main.prepare_interrogator", prepare_mock_interrogator),
        patch("dhfs.main.sleep", sleep),
    ):
        await run_interrogator()

    assert interrogator.interrogate_new_files.await_count == 2
    assert sleep.await_count == (1 if waits else 0)


async def test_new_claimant_id_per_process():
    """Every DHFS process claims files with its own claimant ID."""
    interrogator = AsyncMock(spec=InterrogatorPort)
    interrogator.interrogate_new_files.side_effect = InterrogatorPort.CriticalError(
        "end the loop"
    )
    claimant_ids = []

    @asynccontextmanager
    async def prepare_mock_interrogator(*, config, claimant_id):
        claimant_ids.append(claimant_id)
        yield interrogator

    with (
        patch("dhfs.main.Config", get_config),
        patch("dhfs.main.prepare_interrogator", prepare_mock_interrogator),
    ):
        # Each run stands in for one process
        await run_interrogator()
        await run_interrogator()

    assert len(claimant_ids) == 2
    assert claimant_ids[0] != claimant_ids[1]
    assert all(claimant_id.version == 4 for claimant_id in claimant_ids)
