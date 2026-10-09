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

"""Plumbing for serving the connector's HTTP calls from the API mocks in `apis.py`."""

import ipaddress
import json
import re
from collections.abc import Sequence
from typing import Any

import httpx2

from ghga_connector.core.client import get_ratelimiting_retry_transport

__all__ = [
    "MOCK_API_HOST",
    "MockApiTransport",
    "OffLimitsError",
    "canonical",
    "httpyexpect_error",
    "is_mocked",
    "may_be_reached",
    "mock_health_checks",
    "path_variables",
]

# The host the mocks are served from; `canonical` folds the loopback aliases onto it
MOCK_API_HOST = "127.0.0.1"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def httpyexpect_error(
    status_code: int, exception_id: str, description: str, data: dict[str, Any]
) -> httpx2.Response:
    """The response a GHGA service sends for an error, in the httpyexpect schema."""
    body = {"exception_id": exception_id, "description": description, "data": data}
    return httpx2.Response(
        status_code,
        content=json.dumps(body, default=str),
        headers={"content-type": "application/json"},
    )


def path_variables(request: httpx2.Request, path: str) -> dict[str, str]:
    """Read the `{name}` segments of `path` from the end of the request's path."""
    pattern = re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>[^/]+)", re.escape(path))
    match = re.search(f"{pattern}$", request.url.path)
    if match is None:
        raise AssertionError(f"{request.url.path} does not end in {path}")
    return match.groupdict()


def canonical(url: httpx2.URL) -> httpx2.URL:
    """Fold the loopback aliases onto `MOCK_API_HOST`, leaving any other host alone."""
    return url.copy_with(host=MOCK_API_HOST) if url.host in LOOPBACK_HOSTS else url


class OffLimitsError(RuntimeError):
    """Raised when a test is about to send a request out to the internet."""

    def __init__(self, url: httpx2.URL):
        super().__init__(
            f"A test tried to reach {url}, which is neither one of the mocked GHGA APIs"
            " nor anything else the test environment runs. Mock the API it belongs to"
            " rather than letting the request out."
        )


def may_be_reached(url: httpx2.URL) -> bool:
    """Whether `url` belongs to the test environment and may reach the real network.

    Testcontainers reports loopback, `host.docker.internal` or a private bridge address,
    depending on where Docker runs.
    """
    host = url.host
    if host in LOOPBACK_HOSTS or host.endswith(".internal"):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def is_mocked(url: httpx2.URL, base_urls: Sequence[str]) -> bool:
    """Whether `url` falls under one of the base URLs the mocks are served at."""
    url = canonical(url)
    return any(
        url.scheme == base.scheme
        and url.netloc == base.netloc
        and url.path.startswith(base.path)
        for base in (canonical(httpx2.URL(base_url)) for base_url in base_urls)
    )


class MockApiTransport(httpx2.AsyncBaseTransport):
    """Sends calls to the mocks, lets test environment traffic out, refuses the rest."""

    def __init__(
        self,
        mocks: httpx2.MockTransport,
        base_urls: Sequence[str],
        *,
        limits: httpx2.Limits | None = None,
    ) -> None:
        self._base_urls = tuple(base_urls)
        self._mocked = get_ratelimiting_retry_transport(
            base_transport=mocks, limits=limits
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


def serve_httpx2_get_from(monkeypatch, transport: httpx2.MockTransport) -> None:
    """Answer module level `httpx2.get` calls, which `is_service_healthy` uses."""

    def mock_get(*args: Any, **kwargs: Any) -> httpx2.Response:
        with httpx2.Client(transport=transport) as client:
            return client.get(*args, **kwargs)

    monkeypatch.setattr(httpx2, "get", mock_get)


def mock_health_checks(
    monkeypatch, *, reachable: bool = True, healthy_url: str = ".*"
) -> None:
    """Report the health-checked services as reachable, or refuse the connection.

    Only API URLs matching the regex `healthy_url` count as healthy.
    """

    def check_health(request: httpx2.Request) -> httpx2.Response:
        if reachable and re.search(f"{healthy_url}/health$", str(request.url)):
            return httpx2.Response(200, json={"status": "OK"})
        raise httpx2.ConnectError("mocked connection failure", request=request)

    serve_httpx2_get_from(monkeypatch, httpx2.MockTransport(check_health))
