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

"""Test that the HTTP client keeps its options on every route."""

import pytest

from ghga_datasteward_kit.s3_upload import LegacyConfig
from ghga_datasteward_kit.s3_upload.http_client import (
    USER_AGENT,
    RequestConfigurator,
    httpx_client,
)
from tests.fixtures.config import legacy_config_fixture  # noqa: F401

pytestmark = pytest.mark.asyncio()


async def test_client_keeps_its_options_on_every_route(
    legacy_config_fixture: LegacyConfig,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
):
    """The client sends its User-Agent and timeout, and every route has the pool limits."""
    for name in ("http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:8080")
    RequestConfigurator.configure(legacy_config_fixture)

    async with httpx_client() as client:
        mounts = [mount for mount in client._mounts.values() if mount is not None]
        stacks = [client._transport, *mounts]
        pools = [stack._transport._transport._pool for stack in stacks]

    limit = legacy_config_fixture.client_max_parallel_transfers
    assert client.headers["User-Agent"] == USER_AGENT
    assert client.timeout.read == legacy_config_fixture.client_timeout
    assert len(pools) == 2
    assert all(pool._max_connections == limit for pool in pools)
    assert all(pool._max_keepalive_connections == limit for pool in pools)
