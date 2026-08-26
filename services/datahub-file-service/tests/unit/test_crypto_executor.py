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

"""Unit tests for the dedicated crypto thread pool."""

import asyncio
import threading

import pytest

from dhfs.core.interrogator import CRYPTO_THREAD_COUNT
from tests.fixtures.interrogator import make_interrogator

pytestmark = pytest.mark.asyncio


async def test_crypto_runs_off_the_event_loop():
    """The work must land on a dhfs-crypto thread, not the loop's own thread."""
    loop_thread = threading.current_thread().name
    with make_interrogator() as interrogator:
        thread_name = await interrogator._run_crypto(
            lambda: threading.current_thread().name
        )

    assert thread_name.startswith("dhfs-crypto")
    assert thread_name != loop_thread


async def test_pool_size_is_fixed_not_derived_from_part_budget():
    """A bigger part budget must not widen the pool into its regressive range."""
    with (
        make_interrogator(max_concurrent_parts=2) as narrow,
        make_interrogator(max_concurrent_parts=32) as wide,
    ):
        assert narrow._crypto_executor._max_workers == CRYPTO_THREAD_COUNT
        assert wide._crypto_executor._max_workers == CRYPTO_THREAD_COUNT


async def test_crypto_does_not_block_the_event_loop():
    """While a crypto call runs, the loop must still service the S3 transfers."""
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.005)
            ticks += 1

    ticker_task = asyncio.create_task(ticker())
    try:
        with make_interrogator() as interrogator:
            await interrogator._run_crypto(lambda: threading.Event().wait(0.2))
    finally:
        ticker_task.cancel()

    # A blocking 0.2s call on the loop itself would have allowed zero ticks.
    assert ticks > 5, f"loop only ticked {ticks} times during a 200ms crypto call"


async def test_close_is_idempotent():
    """Shutting the pool down twice must not raise."""
    with make_interrogator() as interrogator:
        interrogator.close()
