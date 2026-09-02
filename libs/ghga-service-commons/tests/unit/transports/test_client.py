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


"""Tests for the composed client: one budget, one flavor on every route."""

import time

import httpx2
import pytest

from ghga_service_commons.transports import (
    CompositeConfig,
    default_base_transport_factory,
    fixed_base_transport_factory,
    get_composite_client,
)
from ghga_service_commons.transports.ratelimiting import RateBudget

HTTP_PROXY_URL = "http://proxy.example.com:8080"
HTTPS_PROXY_URL = "https://secure-proxy.example.com:8443"

_UNPACED = CompositeConfig(min_request_interval=0.0, per_request_jitter=0.0)


@pytest.fixture
def proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the proxy environment variables a deployment behind a proxy would have."""
    monkeypatch.setenv("HTTP_PROXY", HTTP_PROXY_URL)
    monkeypatch.setenv("HTTPS_PROXY", HTTPS_PROXY_URL)


def _routes(client: httpx2.AsyncClient) -> list[httpx2.AsyncBaseTransport]:
    """Every composite stack the client can send through, direct route first."""
    mounts = [mount for mount in client._mounts.values() if mount is not None]
    return [client._transport, *mounts]


def _base_transport(stack) -> httpx2.AsyncBaseTransport:
    """Unwrap retry and rate limiting to reach the transport that sends bytes."""
    return stack._transport._transport


def _budget(stack) -> RateBudget:
    """The pacing state the rate limiting layer of this stack uses."""
    return stack._transport._budget


@pytest.mark.usefixtures("proxy_env")
def test_every_route_shares_one_budget():
    """The configured request rate applies to the client, not to each mount.

    Each mount used to build its own limiter, so setting three proxy variables silently
    tripled the rate a deployment actually used.
    """
    client = get_composite_client(_UNPACED)

    budgets = {id(_budget(route)) for route in _routes(client)}

    assert len(_routes(client)) > 1
    assert len(budgets) == 1


@pytest.mark.usefixtures("proxy_env")
def test_custom_transport_serves_every_route():
    """A supplied transport is used for proxy mounts too, not stranded behind them.

    Mounts take precedence over a client's own transport, so a custom transport used to
    go silently unused whenever proxy variables were set.
    """
    mock = httpx2.MockTransport(lambda request: httpx2.Response(200))
    client = get_composite_client(
        _UNPACED, make_base_transport=fixed_base_transport_factory(mock)
    )

    assert all(_base_transport(route) is mock for route in _routes(client))


@pytest.mark.usefixtures("proxy_env")
def test_factory_is_called_once_per_route_with_its_proxy():
    """A wrapper transport can be combined with proxying, which was impossible before."""
    seen: list[str | None] = []

    def instrumented(proxy: str | None) -> httpx2.AsyncBaseTransport:
        seen.append(proxy)
        return httpx2.MockTransport(lambda request: httpx2.Response(200))

    get_composite_client(_UNPACED, make_base_transport=instrumented)

    assert None in seen
    assert sorted(p for p in seen if p) == sorted([HTTP_PROXY_URL, HTTPS_PROXY_URL])


@pytest.mark.usefixtures("proxy_env")
def test_limits_reach_the_proxy_mounts():
    """Pool sizing applies to proxied routes, not only to the direct one.

    The proxy helper used to build its transports without limits and hand them on as a
    base transport, where limits are ignored, so a requested pool silently stayed at 100.
    """
    client = get_composite_client(_UNPACED, limits=httpx2.Limits(max_connections=7))

    pools = [_base_transport(route)._pool._max_connections for route in _routes(client)]  # type: ignore[attr-defined]

    assert pools == [7] * len(pools)


@pytest.mark.usefixtures("proxy_env")
def test_trust_env_false_mounts_no_proxies():
    """The standard escape hatch for distrusting the environment is honored."""
    client = get_composite_client(_UNPACED, trust_env=False)

    assert client._mounts == {}


def test_limits_and_a_custom_factory_are_mutually_exclusive():
    """Limits size the default transport, so they cannot also size one you built."""
    with pytest.raises(ValueError, match="limits size the default base transport"):
        get_composite_client(
            _UNPACED,
            limits=httpx2.Limits(max_connections=7),
            make_base_transport=default_base_transport_factory(),
        )


def test_client_keyword_arguments_are_passed_through():
    """Remaining keyword arguments reach the underlying client."""
    client = get_composite_client(_UNPACED, timeout=42.0)

    assert client.timeout.connect == 42.0


@pytest.mark.asyncio
async def test_retry_after_outlasts_the_retry_backoff():
    """A 429 asking for longer than the backoff still waits the full Retry-After.

    The two waits run in sequence: the retry layer sleeps its backoff, then the next
    attempt blocks on the budget's floor. This is the property the removed Should-Wait
    signal used to protect.
    """
    attempts = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        attempts.append(time.monotonic())
        if len(attempts) == 1:
            return httpx2.Response(429, headers={"Retry-After": "1"})
        return httpx2.Response(200)

    config = CompositeConfig(
        min_request_interval=0.0, per_request_jitter=0.0, client_num_retries=2
    )
    client = get_composite_client(
        config,
        trust_env=False,
        make_base_transport=fixed_base_transport_factory(httpx2.MockTransport(respond)),
    )

    async with client:
        response = await client.get("http://example.com")

    assert response.status_code == 200
    assert attempts[1] - attempts[0] >= 1
