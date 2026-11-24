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


"""Tests for the metrics the REST app exports"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from dlqs import inject
from dlqs.inject import prepare_rest_app
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


@pytest.mark.parametrize("enabled", [True, False])
async def test_dead_letter_gauge(monkeypatch: pytest.MonkeyPatch, enabled: bool):
    """The REST app reports the dead letter count only when metrics are enabled."""
    gauges: list[dict] = []

    @asynccontextmanager
    async def fake_refresh_gauge(**kwargs):
        gauges.append(kwargs)
        yield

    monkeypatch.setattr(inject, "refresh_gauge", fake_refresh_gauge)
    config = get_config(enable_opentelemetry=enabled, enable_otel_metrics=enabled)
    dlq_manager = AsyncMock()

    async with prepare_rest_app(config=config, dlq_manager_override=dlq_manager):
        pass

    if not enabled:
        assert gauges == []
        return
    assert len(gauges) == 1
    assert gauges[0]["name"] == "dlqs.dead_letters"
    assert gauges[0]["read"] is dlq_manager.count_dead_letters
