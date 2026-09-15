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
#

"""Tests for the Kafka test container harness from `hexkit.providers.akafka.testutils`."""

from itertools import repeat
from typing import Any
from unittest.mock import AsyncMock

import pytest
from aiokafka.errors import NodeNotReadyError

from hexkit.providers.akafka import testutils
from hexkit.providers.akafka.testutils import KafkaContainerFixture

pytestmark = pytest.mark.asyncio()

KAFKA_SERVERS = ["localhost:9093"]


def patch_admin_client(monkeypatch: pytest.MonkeyPatch, outcomes: Any) -> None:
    """Make each admin client that gets constructed yield the next outcome.

    An outcome is either an exception to raise or the value `list_topics` returns.
    A fresh client is built per attempt, so the outcomes are consumed across attempts.
    """
    remaining = iter(outcomes)

    def build_client(**_kwargs) -> AsyncMock:
        client = AsyncMock()
        client.list_topics.side_effect = [next(remaining)]
        return client

    monkeypatch.setattr(testutils, "AIOKafkaAdminClient", build_client)
    monkeypatch.setattr(testutils, "BROKER_REGISTRATION_POLL_INTERVAL", 0)


async def test_wait_for_broker_retries_until_registered(
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that the wait rides out the window in which no broker is registered."""
    not_ready = NodeNotReadyError("Attempt to send a request to node")
    patch_admin_client(monkeypatch, [not_ready, not_ready, ["some-topic"]])

    await KafkaContainerFixture._wait_for_broker(KAFKA_SERVERS, timeout=5)


async def test_wait_for_broker_gives_up_after_the_timeout(
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that a broker which never registers is reported, not waited on forever."""
    not_ready = NodeNotReadyError("Attempt to send a request to node")
    patch_admin_client(monkeypatch, repeat(not_ready))

    with pytest.raises(RuntimeError, match="did not register within") as exc_info:
        await KafkaContainerFixture._wait_for_broker(KAFKA_SERVERS, timeout=0.05)

    assert exc_info.value.__cause__ is not_ready
