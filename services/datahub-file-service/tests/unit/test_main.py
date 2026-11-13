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
    async def prepare_mock_interrogator(*, config):
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
