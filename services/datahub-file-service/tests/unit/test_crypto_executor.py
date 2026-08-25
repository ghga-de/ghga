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

"""Unit tests for the dedicated crypto thread pool.

The pool exists so that a part's decrypt/re-encrypt/verify chain - which contains no
await and therefore blocks in one stretch - cannot stall the S3 transfers of the parts
running alongside it. Its size is fixed at two rather than derived from
`max_concurrent_parts`: the crypto stages peak at two threads and regress beyond that,
so scaling the pool with the part budget makes throughput worse, not better.
"""

import asyncio
import threading
from unittest.mock import MagicMock

import pytest

from dhfs.core.interrogator import CRYPTO_THREAD_COUNT, Interrogator
from tests.fixtures.config import get_config
from tests.fixtures.utils import DHFS_CRYPT4GH_PRIVATE_KEY_PATH

pytestmark = pytest.mark.asyncio


def build_interrogator(max_concurrent_parts: int = 8) -> Interrogator:
    """An Interrogator with mocked-out collaborators - only threading is exercised."""
    config = get_config(
        data_hub_crypt4gh_private_key_path=DHFS_CRYPT4GH_PRIVATE_KEY_PATH,
        max_concurrent_parts=max_concurrent_parts,
    )
    return Interrogator(
        config=config, central_client=MagicMock(), s3_client=MagicMock()
    )


async def test_crypto_runs_off_the_event_loop():
    """The work must land on a dhfs-crypto thread, not the loop's own thread."""
    interrogator = build_interrogator()
    loop_thread = threading.current_thread().name
    try:
        thread_name = await interrogator._run_crypto(
            lambda: threading.current_thread().name
        )
    finally:
        interrogator.close()

    assert thread_name.startswith("dhfs-crypto")
    assert thread_name != loop_thread


async def test_pool_size_is_fixed_not_derived_from_part_budget():
    """A bigger part budget must not widen the pool into its regressive range."""
    narrow = build_interrogator(max_concurrent_parts=2)
    wide = build_interrogator(max_concurrent_parts=32)
    try:
        assert narrow._crypto_executor._max_workers == CRYPTO_THREAD_COUNT
        assert wide._crypto_executor._max_workers == CRYPTO_THREAD_COUNT
    finally:
        narrow.close()
        wide.close()


async def test_crypto_does_not_block_the_event_loop():
    """While a crypto call is running, the loop must still service other tasks.

    This is the whole point of the pool: the S3 transfers of concurrent parts are
    exactly the 'other tasks' that must keep progressing.
    """
    interrogator = build_interrogator()
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.005)
            ticks += 1

    ticker_task = asyncio.create_task(ticker())
    try:
        await interrogator._run_crypto(lambda: threading.Event().wait(0.2))
    finally:
        ticker_task.cancel()
        interrogator.close()

    # A blocking 0.2s call on the loop itself would have allowed zero ticks.
    assert ticks > 5, f"loop only ticked {ticks} times during a 200ms crypto call"


async def test_close_is_idempotent():
    """Shutting the pool down twice must not raise."""
    interrogator = build_interrogator()
    interrogator.close()
    interrogator.close()
