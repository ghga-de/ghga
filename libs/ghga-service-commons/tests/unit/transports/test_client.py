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

"""Tests for the client routes: the same stack on every route."""

import asyncio
import time
from collections import Counter
from itertools import pairwise

import httpx2
import pytest

from ghga_service_commons.transports import (
    ClientRoutes,
    TransportConfig,
    client_routes,
    default_base_transport_factory,
)

# RFC 6761 reserves .invalid for names that never resolve,
# so no request from these tests can reach a real host
HTTP_PROXY_URL = "http://proxy.invalid:8080"
HTTPS_PROXY_URL = "https://secure-proxy.invalid:8443"
SERVICE_HOST = "service.invalid"
DIRECT_HOST = "direct.invalid"

_UNPACED = TransportConfig(min_request_interval=0.0, per_request_jitter=0.0)
_STEP = 0.05


@pytest.fixture
def proxy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the proxy environment variables a deployment behind a proxy would have.

    Proxy variables from the surrounding shell are cleared first: urllib prefers the
    lowercase ones, and ALL_PROXY or NO_PROXY would change the routes.
    """
    for scheme in ("http", "https", "all", "no"):
        monkeypatch.delenv(f"{scheme}_proxy", raising=False)
        monkeypatch.delenv(f"{scheme.upper()}_PROXY", raising=False)
    monkeypatch.setenv("HTTP_PROXY", HTTP_PROXY_URL)
    monkeypatch.setenv("HTTPS_PROXY", HTTPS_PROXY_URL)


def _stacks(routes: ClientRoutes) -> list[httpx2.AsyncBaseTransport]:
    """Every composite stack a client can send through, direct route first."""
    mounts = [mount for mount in routes["mounts"].values() if mount is not None]
    return [routes["transport"], *mounts]


def _base_transport(stack) -> httpx2.AsyncBaseTransport:
    """Unwrap retry and rate limiting to reach the transport that sends bytes."""
    return stack._transport._transport


def test_custom_transport_serves_every_route(proxy_env: None):
    """A supplied transport serves the proxy mounts too, not just the direct route."""
    mock = httpx2.MockTransport(lambda request: httpx2.Response(200))
    routes = client_routes(_UNPACED, make_base_transport=lambda _: mock)

    assert all(_base_transport(stack) is mock for stack in _stacks(routes))


def test_factory_is_called_once_per_route_with_its_proxy(proxy_env: None):
    """The factory builds a transport per route, so wrappers and proxying can combine."""
    seen: list[str | None] = []

    def instrumented(proxy: str | None) -> httpx2.AsyncBaseTransport:
        seen.append(proxy)
        return httpx2.MockTransport(lambda request: httpx2.Response(200))

    client_routes(_UNPACED, make_base_transport=instrumented)

    assert Counter(seen) == Counter([None, HTTP_PROXY_URL, HTTPS_PROXY_URL])


def test_limits_reach_the_proxy_mounts(proxy_env: None):
    """Pool sizing applies to proxied routes, not only to the direct one."""
    limits = httpx2.Limits(
        max_connections=7, max_keepalive_connections=3, keepalive_expiry=11
    )
    routes = client_routes(
        _UNPACED, make_base_transport=default_base_transport_factory(limits=limits)
    )

    pools = [_base_transport(stack)._pool for stack in _stacks(routes)]  # type: ignore[attr-defined]

    assert len(pools) == 3
    assert all(pool._max_connections == limits.max_connections for pool in pools)
    assert all(
        pool._max_keepalive_connections == limits.max_keepalive_connections
        for pool in pools
    )
    assert all(pool._keepalive_expiry == limits.keepalive_expiry for pool in pools)


@pytest.mark.asyncio
async def test_client_options_reach_every_route(
    proxy_env: None, monkeypatch: pytest.MonkeyPatch
):
    """The client's timeout, headers and event hooks apply on every route it sends through."""
    monkeypatch.setenv("NO_PROXY", DIRECT_HOST)
    sent: list[tuple[str | None, httpx2.Request]] = []
    hooked: list[str] = []

    def make_base_transport(proxy: str | None) -> httpx2.AsyncBaseTransport:
        def respond(request: httpx2.Request) -> httpx2.Response:
            sent.append((proxy, request))
            return httpx2.Response(200)

        return httpx2.MockTransport(respond)

    async def hook(request: httpx2.Request) -> None:
        hooked.append(str(request.url))

    routes = client_routes(_UNPACED, make_base_transport=make_base_transport)
    async with httpx2.AsyncClient(
        timeout=12.0,
        headers={"User-Agent": "routes-test"},
        event_hooks={"request": [hook]},
        **routes,
    ) as client:
        urls = [
            f"http://{SERVICE_HOST}/",
            f"https://{SERVICE_HOST}/",
            f"https://{DIRECT_HOST}/",
        ]
        for url in urls:
            await client.get(url)

    assert [proxy for proxy, _ in sent] == [HTTP_PROXY_URL, HTTPS_PROXY_URL, None]
    assert hooked == urls
    for _, request in sent:
        assert request.headers["User-Agent"] == "routes-test"
        assert request.extensions["timeout"]["read"] == 12.0


@pytest.mark.asyncio
async def test_retry_after_outlasts_the_retry_backoff():
    """A 429 asking for longer than the backoff still waits the full Retry-After.

    The retry layer sleeps its backoff, then the next attempt blocks on the budget's
    floor, so the longer of the two decides.
    """
    attempts = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        attempts.append(time.monotonic())
        if len(attempts) == 1:
            return httpx2.Response(429, headers={"Retry-After": "1"})
        return httpx2.Response(200)

    # Without backoff, only the Retry-After floor can hold the second attempt back.
    config = TransportConfig(
        min_request_interval=0.0,
        per_request_jitter=0.0,
        client_num_retries=2,
        client_exponential_backoff_max=0,
    )
    mock = httpx2.MockTransport(respond)
    routes = client_routes(config, make_base_transport=lambda _: mock)

    async with httpx2.AsyncClient(**routes) as client:
        response = await client.get(f"http://{SERVICE_HOST}")

    assert response.status_code == 200
    assert attempts[1] - attempts[0] >= 1


@pytest.mark.asyncio
async def test_request_pacing_works_for_proxy_mounts(proxy_env: None):
    """Ensure requests of one scope wait for each other on the same proxy mount."""
    sent: dict[str, list[float]] = {"upload": [], "download": []}

    def respond(request: httpx2.Request) -> httpx2.Response:
        sent[request.url.path.split("/")[1]].append(time.monotonic())
        return httpx2.Response(200)

    config = TransportConfig(min_request_interval=_STEP, per_request_jitter=0.0)
    mock = httpx2.MockTransport(respond)
    routes = client_routes(config, make_base_transport=lambda _: mock)
    async with httpx2.AsyncClient(**routes) as client:
        await asyncio.gather(
            *(
                client.get(f"https://{SERVICE_HOST}/{scope}/{n}")
                for scope in sent
                for n in range(3)
            )
        )

    uploads = sorted(sent["upload"])
    # Check pacing, accounting vor some delays so the test isn't flaky
    assert all(later - earlier >= _STEP * 0.9 for earlier, later in pairwise(uploads))
    assert abs(min(sent["download"]) - uploads[0]) < _STEP
