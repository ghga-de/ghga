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
"""Unit tests for the Prometheus metrics adapter"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from dlqs.adapters.inbound import metrics
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio


async def test_dead_letter_collector_collect():
    """Verify the collector fetches the count from the manager via the event loop
    and reports it as a single gauge sample.
    """
    dlq_manager = AsyncMock(spec=DLQManagerPort)
    dlq_manager.count_dead_letters.return_value = 7
    loop = asyncio.get_running_loop()
    collector = metrics.DeadLetterCollector(dlq_manager=dlq_manager, loop=loop)

    # collect() is synchronous and blocks on a coroutine scheduled on `loop`, so run
    # it in a thread to let the loop keep servicing that coroutine concurrently -
    # mirroring how the real metrics server thread calls it.
    families = await asyncio.to_thread(lambda: list(collector.collect()))

    assert len(families) == 1
    (family,) = families
    assert family.name == "dlqs_dead_letters_total"
    (sample,) = family.samples
    assert sample.value == 7
    dlq_manager.count_dead_letters.assert_awaited_once()


async def test_start_metrics_server_skips_when_multiple_workers(
    caplog, monkeypatch: pytest.MonkeyPatch
):
    """Verify the server is not started and an error is logged when workers != 1."""
    config = get_config(workers=2)
    dlq_manager = AsyncMock(spec=DLQManagerPort)

    start_http_server = Mock()
    register = Mock()
    monkeypatch.setattr(metrics, "start_http_server", start_http_server)
    monkeypatch.setattr(metrics.REGISTRY, "register", register)

    with caplog.at_level("ERROR"):
        metrics.start_metrics_server(config=config, dlq_manager=dlq_manager)

    start_http_server.assert_not_called()
    register.assert_not_called()
    assert any("workers=2" in message for message in caplog.messages)


async def test_start_metrics_server_starts_with_single_worker(
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify the collector is registered and the server started when workers == 1."""
    config = get_config(workers=1, metrics_port=9999)
    dlq_manager = AsyncMock(spec=DLQManagerPort)

    start_http_server = Mock()
    register = Mock()
    monkeypatch.setattr(metrics, "start_http_server", start_http_server)
    monkeypatch.setattr(metrics.REGISTRY, "register", register)

    metrics.start_metrics_server(config=config, dlq_manager=dlq_manager)

    register.assert_called_once()
    (registered_collector,) = register.call_args.args
    assert isinstance(registered_collector, metrics.DeadLetterCollector)
    start_http_server.assert_called_once_with(port=9999, addr=config.host)
