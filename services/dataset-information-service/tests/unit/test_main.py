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


"""Tests for the entrypoints"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from dins import main
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


@pytest.fixture(name="calls")
def patched_main(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace what the entrypoints call and record the order of the calls."""
    calls: list[str] = []
    config = get_config()

    @asynccontextmanager
    async def prepare(*, config):
        calls.append("prepare")
        yield MagicMock(run=AsyncMock())

    def configure_opentelemetry(*, service_name, config):
        calls.append(f"opentelemetry:{service_name}")

    monkeypatch.setattr(main, "Config", lambda: config)
    monkeypatch.setattr(main, "configure_logging", MagicMock())
    monkeypatch.setattr(main, "configure_opentelemetry", configure_opentelemetry)
    monkeypatch.setattr(main, "prepare_rest_app", prepare)
    monkeypatch.setattr(main, "prepare_event_subscriber", prepare)
    monkeypatch.setattr(main, "run_server", AsyncMock())
    return calls


async def test_run_rest_configures_opentelemetry_first(calls: list[str]):
    """The REST app sets up OpenTelemetry before it builds the app."""
    await main.run_rest()
    assert calls == [f"opentelemetry:{get_config().service_name}", "prepare"]


async def test_consume_events_configures_opentelemetry_first(calls: list[str]):
    """The consumer sets up OpenTelemetry before it builds the subscriber."""
    await main.consume_events(run_forever=False)
    assert calls == [f"opentelemetry:{get_config().service_name}", "prepare"]
