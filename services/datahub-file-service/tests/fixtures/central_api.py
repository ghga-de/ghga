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

"""A mock of the GHGA Central API, built on the service commons `MockRouter`."""

__all__ = [
    "CentralApiMock",
    "ResponseHandler",
    "capture",
    "fail_to_connect",
    "get_mocked_httpx_client",
    "respond",
]

import json
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx2

from dhfs.adapters.outbound.central import (
    INTERROGATION_REPORTS_PATH,
    REMOVABLE_FILES_PATH,
    UPLOADS_PATH,
    CentralClientConfig,
)
from dhfs.adapters.outbound.http import HttpClientConfig, get_configured_httpx_client
from ghga_service_commons.api.mock_router import MockRouter

ResponseHandler = Callable[[httpx2.Request], httpx2.Response]


def respond(status_code: int, json: Any = None) -> ResponseHandler:
    """Make a handler that always answers with the same status code and JSON body.

    A `json` of `None` means the response carries no body at all.
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code=status_code, json=json)

    return handler


def capture(
    into: list, status_code: int = 201, response_json: Any = None
) -> ResponseHandler:
    """Make a handler that records each request's JSON body into `into`."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        into.append(json.loads(request.content))
        return httpx2.Response(status_code=status_code, json=response_json or {})

    return handler


def fail_to_connect(reason: str = "All connection attempts failed") -> ResponseHandler:
    """Make a handler that simulates the Central API being unreachable."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(reason, request=request)

    return handler


class CentralApiMock:
    """A mock of the GHGA Central API endpoints that the DHFS talks to.

    Each endpoint answers with the handler assigned to `on_fetch_new_uploads`,
    `on_get_removable_files` or `on_submit_report`. Tests can swap those out with
    `respond(...)`, `fail_to_connect(...)` or any other callable taking the request.
    Every request that reaches the mock is recorded in `requests`.

    By default the transport returned by `as_transport()` answers *every* request, so a
    test cannot accidentally reach the network. Pass `passthrough=True` where the same
    client also has to carry real traffic - the S3 testcontainer, in practice.
    """

    def __init__(
        self, *, config: CentralClientConfig, passthrough: bool = False
    ) -> None:
        self._base_url = str(config.central_api_url).rstrip("/")
        self._passthrough = passthrough
        base_path = httpx2.URL(self._base_url).path

        self.requests: list[httpx2.Request] = []
        self.on_fetch_new_uploads: ResponseHandler = respond(200, json=[])
        self.on_get_removable_files: ResponseHandler = respond(200, json=[])
        self.on_submit_report: ResponseHandler = respond(201, json={})

        router: MockRouter = MockRouter()

        @router.get(f"{base_path}{UPLOADS_PATH}")
        def fetch_new_uploads(
            storage_alias: str, request: httpx2.Request
        ) -> httpx2.Response:
            return self._handle(request, self.on_fetch_new_uploads)

        @router.post(f"{base_path}{REMOVABLE_FILES_PATH}")
        def get_removable_files(
            storage_alias: str, request: httpx2.Request
        ) -> httpx2.Response:
            return self._handle(request, self.on_get_removable_files)

        @router.post(f"{base_path}{INTERROGATION_REPORTS_PATH}")
        def submit_interrogation_report(
            storage_alias: str, request: httpx2.Request
        ) -> httpx2.Response:
            return self._handle(request, self.on_submit_report)

        self._router = router

    def _handle(
        self, request: httpx2.Request, handler: ResponseHandler
    ) -> httpx2.Response:
        """Record the request and let the currently assigned handler answer it."""
        self.requests.append(request)
        return handler(request)

    def as_transport(self) -> httpx2.AsyncBaseTransport:
        """Return a transport answering Central API requests with this mock.

        Requests to anything else raise, unless the mock was built with
        `passthrough=True`, in which case they are sent over the network as usual.
        """
        mock_transport = self._router.as_transport()
        if not self._passthrough:
            return mock_transport
        return _CentralApiRoutingTransport(
            mock_transport=mock_transport, base_url=self._base_url
        )


class _CentralApiRoutingTransport(httpx2.AsyncBaseTransport):
    """Splits traffic between a Central API mock transport and the actual network."""

    def __init__(self, *, mock_transport: httpx2.MockTransport, base_url: str) -> None:
        self._mock_transport = mock_transport
        self._base_url = base_url
        self._network_transport = httpx2.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Dispatch the request based on whether it targets the Central API."""
        if str(request.url).startswith(self._base_url):
            return await self._mock_transport.handle_async_request(request)
        return await self._network_transport.handle_async_request(request)

    async def aclose(self) -> None:
        """Close the transport used for the requests that aren't mocked."""
        await self._network_transport.aclose()


@asynccontextmanager
async def get_mocked_httpx_client(
    *, config: HttpClientConfig, central_api: CentralApiMock
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Drop-in for `get_configured_httpx_client` that answers Central API calls with
    `central_api` while leaving all other traffic untouched.
    """
    async with get_configured_httpx_client(
        config=config, base_transport=central_api.as_transport()
    ) as client:
        yield client
