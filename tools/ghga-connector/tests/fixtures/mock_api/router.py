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

"""Plumbing for serving the connector's HTTP calls from the API mocks.

The mocked APIs themselves live in `apis.py`; this module only knows where a request is
allowed to go, and how to build the one transport that decides it.
"""

import ipaddress
from collections.abc import Sequence
from typing import Any

import httpx2

from ghga_connector.core.client import get_ratelimiting_retry_transport
from ghga_service_commons.api.mock_api import (
    ApiMock,
    RoutingTransport,
    fail_to_connect,
    respond,
)

__all__ = [
    "MOCK_API_HOST",
    "MockApiTransport",
    "OffLimitsError",
    "canonical",
    "is_mocked",
    "may_be_reached",
    "mock_health_checks",
]

# The host the mocked GHGA APIs are served from, and the other spellings of it they also
# answer to. `canonical` folds those onto `MOCK_API_HOST`, so everything downstream -
# patterns included - only ever sees the one spelling.
MOCK_API_HOST = "127.0.0.1"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def canonical(url: httpx2.URL) -> httpx2.URL:
    """Fold the loopback aliases onto `MOCK_API_HOST`, leaving any other host alone.

    Doing this once, on the way into the transport, is what lets everything downstream
    assume the single spelling - so a call to `localhost` reaches a mock registered on
    `127.0.0.1` without every pattern having to spell out the alternatives.
    """
    return url.copy_with(host=MOCK_API_HOST) if url.host in LOOPBACK_HOSTS else url


class OffLimitsError(RuntimeError):
    """Raised when a test is about to send a request out to the internet."""

    def __init__(self, url: httpx2.URL):
        """Name the request that was refused, and what to do about it."""
        super().__init__(
            f"A test tried to reach {url}, which is neither one of the mocked GHGA APIs"
            " nor anything else the test environment runs. Mock the API it belongs to"
            " rather than letting the request out."
        )


def may_be_reached(url: httpx2.URL) -> bool:
    """Whether a request to `url` may leave the test suite for the real network.

    Only what the test environment itself runs may be reached. Testcontainers reports a
    container's address as whatever the Docker host happens to be - loopback when Docker
    is local, `host.docker.internal` from inside a devcontainer, a private bridge address
    when neither - so all three pass, while the internet at large must not.
    """
    host = url.host
    if host in LOOPBACK_HOSTS or host.endswith(".internal"):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def is_mocked(url: httpx2.URL, base_urls: Sequence[str]) -> bool:
    """Whether `url` falls under one of the base URLs the mocks registered on.

    This is what makes the guard exact rather than a guess: a URL is served by a mock
    precisely when a mock claimed it, so a mocked API growing a port or moving to
    another path cannot quietly start escaping to the network.
    """
    url = canonical(url)
    return any(
        url.scheme == base.scheme
        and url.netloc == base.netloc
        and url.path.startswith(base.path)
        for base in (canonical(httpx2.URL(base_url)) for base_url in base_urls)
    )


class MockApiTransport(httpx2.AsyncBaseTransport):
    """Sends GHGA API calls to the mocks and refuses anything bound for the internet.

    Requests to whatever else the test environment runs - the S3 testcontainer, whose
    presigned URLs the mocked APIs hand out - go over the network as usual, since the
    point of those URLs is that they address real storage.
    """

    def __init__(
        self,
        mocks: Sequence[ApiMock],
        *,
        limits: httpx2.Limits | None = None,
    ) -> None:
        """Route to `mocks`, and let out only what the test environment runs.

        Each leg gets its own retry transport, so a mocked response passes through the
        same retry and rate limiting stack the connector uses in earnest without sharing
        that stack's state with the traffic going to the testcontainer.
        """
        self._base_urls = tuple(mock.base_url for mock in mocks)
        self._mocked = get_ratelimiting_retry_transport(
            base_transport=RoutingTransport(*mocks), limits=limits
        )
        self._network = get_ratelimiting_retry_transport(limits=limits)

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Send the request wherever it is allowed to go, or refuse to send it."""
        request.url = canonical(request.url)
        if is_mocked(request.url, self._base_urls):
            return await self._mocked.handle_async_request(request)
        if may_be_reached(request.url):
            return await self._network.handle_async_request(request)
        raise OffLimitsError(request.url)


def _serve_httpx2_get_from(monkeypatch, mock: ApiMock) -> None:
    """Answer module level `httpx2.get` calls from `mock`.

    `is_service_healthy` checks health endpoints with a module level `httpx2.get` rather
    than the client built by `async_client`, so those calls cannot be routed through the
    client's transport and `httpx2.get` itself has to be replaced. Only `httpx2.get` is,
    rather than the whole module as `ApiMock.patch_httpx_module` would: everything else
    the connector sends goes through its own client, and has to keep reaching the
    transport that decides where a request may go.
    """
    transport = mock.as_transport()

    def mock_get(*args: Any, **kwargs: Any) -> httpx2.Response:
        """Stand in for `httpx2.get`, answering out of the mock.

        The signature mirrors `httpx2.get` rather than the call `check_url` happens to
        make, so rewriting that call site doesn't break the stand-in.
        """
        with httpx2.Client(transport=transport) as client:
            return client.get(*args, **kwargs)

    monkeypatch.setattr(httpx2, "get", mock_get)


def mock_health_checks(
    monkeypatch, *, reachable: bool = True, healthy_url: str = ".*"
) -> None:
    """Report the services the connector health checks as reachable or unreachable.

    `healthy_url` is a regex for the API URLs to report as healthy, defaulting to all of
    them. Pass `re.escape(...)` of a single API URL to pin down which URL the connector
    derives its health endpoint from; anything else then refuses the connection.
    """
    health_endpoints = ApiMock()

    if reachable:
        health_endpoints.add(
            method="GET",
            path=f"{healthy_url}/health",
            handler=respond(200, json={"status": "OK"}),
        )

    # Endpoints are matched in registration order, so this only catches what is left.
    health_endpoints.add(
        method="GET", path=".*", handler=fail_to_connect("mocked connection failure")
    )

    _serve_httpx2_get_from(monkeypatch, health_endpoints)
