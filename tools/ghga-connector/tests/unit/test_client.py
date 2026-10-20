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

"""Test that the connector's HTTP client keeps its options on every route."""

from functools import partial

import pytest

from ghga_connector.constants import KEEPALIVE_EXPIRY, POOL_HEADROOM, TIMEOUT
from ghga_connector.core.client import async_client
from ghga_service_commons.http.correlation import _cid_request_hook
from tests.fixtures.config import get_test_config

pytestmark = pytest.mark.asyncio()


@pytest.mark.parametrize("purpose, parts", [("upload", 4), ("download", 6)])
async def test_client_keeps_its_options_on_every_route(
    purpose: str, parts: int, monkeypatch: pytest.MonkeyPatch
):
    """The client keeps its timeout and correlation hook, and every route its pool."""
    for name in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")
    config = get_test_config(max_concurrent_uploads=4, max_concurrent_downloads=6)
    monkeypatch.setattr("ghga_connector.config.CONFIG", config)

    async with async_client(purpose=purpose) as client:  # type: ignore[arg-type]
        mounts = [mount for mount in client._mounts.values() if mount is not None]
        stacks = [client._transport, *mounts]
        pools = [stack._transport._transport._pool for stack in stacks]
        hooks = client.event_hooks["request"]

    assert client.timeout.read == TIMEOUT
    assert any(isinstance(h, partial) and h.func is _cid_request_hook for h in hooks)
    assert len(pools) == 2
    assert all(pool._max_connections == parts + POOL_HEADROOM for pool in pools)
    assert all(pool._keepalive_expiry == KEEPALIVE_EXPIRY for pool in pools)
