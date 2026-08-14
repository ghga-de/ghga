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

Crypto and hashing must not run on the event loop's default executor: hexkit's S3
provider dispatches every boto3 call there, so sharing it lets CPU work squeeze out
the S3 round trips the part pipeline is supposed to overlap it with.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from dhfs.core.interrogator import Interrogator
from tests.fixtures.config import get_config
from tests.fixtures.utils import DHFS_CRYPT4GH_PRIVATE_KEY_PATH

pytestmark = pytest.mark.asyncio


def build_interrogator(max_concurrent_parts: int = 4) -> Interrogator:
    """An Interrogator with mocked-out collaborators - only threading is exercised."""
    config = get_config(
        data_hub_crypt4gh_private_key_path=DHFS_CRYPT4GH_PRIVATE_KEY_PATH,
        max_concurrent_parts=max_concurrent_parts,
    )
    return Interrogator(
        config=config, central_client=MagicMock(), s3_client=MagicMock()
    )


async def test_crypto_runs_on_its_own_pool():
    """The work must land on a dhfs-crypto thread, not a default-executor one."""
    interrogator = build_interrogator()
    try:
        thread_name = await interrogator._run_crypto(
            lambda: threading.current_thread().name
        )
    finally:
        interrogator.close()

    assert thread_name.startswith("dhfs-crypto")


async def test_saturated_default_executor_does_not_stall_crypto():
    """This is the regression: a fully occupied default executor must not block crypto.

    The default executor is capped at min(32, cpu_count + 4), which is as few as 5 or 6
    workers on a CPU-limited container - fewer than max_concurrent_parts allows in
    flight. Pinning it to a single worker here reproduces that in miniature.
    """
    loop = asyncio.get_running_loop()
    starved_executor = ThreadPoolExecutor(max_workers=1)
    loop.set_default_executor(starved_executor)

    release = threading.Event()
    # Occupy the one and only default worker, exactly as a slow boto3 call would
    blocker = asyncio.create_task(asyncio.to_thread(release.wait, 10))
    await asyncio.sleep(0.05)

    interrogator = build_interrogator()
    try:
        # Would time out if the crypto call had to queue behind the blocker
        thread_name = await asyncio.wait_for(
            interrogator._run_crypto(lambda: threading.current_thread().name),
            timeout=2,
        )
    finally:
        release.set()
        await blocker
        interrogator.close()
        starved_executor.shutdown(wait=False)

    assert thread_name.startswith("dhfs-crypto")


async def test_pool_has_one_worker_per_part_slot():
    """A part runs at most one crypto call at a time, so the budgets have to match.

    Fewer workers than slots would silently serialize parts that the semaphore had
    already admitted.
    """
    max_concurrent_parts = 3
    interrogator = build_interrogator(max_concurrent_parts=max_concurrent_parts)

    entered = threading.Barrier(max_concurrent_parts, timeout=5)
    try:
        # Every call blocks until all of them are running, so this only returns if
        #  the pool really can run that many at once
        await asyncio.wait_for(
            asyncio.gather(
                *(
                    interrogator._run_crypto(entered.wait)
                    for _ in range(max_concurrent_parts)
                )
            ),
            timeout=5,
        )
    finally:
        interrogator.close()


async def test_close_is_idempotent():
    """Shutdown runs from a context manager's finally, which can be reached twice."""
    interrogator = build_interrogator()
    interrogator.close()
    interrogator.close()
