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

"""A mock of the GHGA Central API, built on the service commons `MockApi`."""

__all__ = ["CentralApiMock", "get_mocked_httpx_client"]

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx2

from dhfs.adapters.outbound.central import (
    INTERROGATION_REPORTS_PATH,
    REMOVABLE_FILES_PATH,
    UPLOADS_PATH,
    CentralClientConfig,
)
from dhfs.adapters.outbound.http import HttpClientConfig, get_configured_httpx_client
from ghga_service_commons.http.mock_api import MockApi, ResponseHandler, respond


class CentralApiMock(MockApi):
    """A mock of the Central API endpoints the DHFS calls, succeeding by default."""

    def __init__(self, *, config: CentralClientConfig) -> None:
        super().__init__(str(config.central_api_url))
        self.on_fetch_new_uploads: ResponseHandler = respond(200, json=[])
        self.on_get_removable_files: ResponseHandler = respond(200, json=[])
        self.on_submit_report: ResponseHandler = respond(201, json={})
        self.route("GET", UPLOADS_PATH, "on_fetch_new_uploads")
        self.route("POST", REMOVABLE_FILES_PATH, "on_get_removable_files")
        self.route("POST", INTERROGATION_REPORTS_PATH, "on_submit_report")

    @property
    def submitted_reports(self) -> list[dict]:
        """The JSON bodies of the interrogation reports submitted so far."""
        return [
            json.loads(request.content)
            for request in self.requests
            if request.url.path.endswith("/interrogation-reports")
        ]


class _CentralApiRoutingTransport(httpx2.AsyncBaseTransport):
    """Sends Central API calls to the mock and everything else to the network."""

    def __init__(self, *, mock_transport: httpx2.MockTransport, base_url: str) -> None:
        self._mock_transport = mock_transport
        self._base_url = base_url.rstrip("/")
        self._network_transport = httpx2.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Dispatch the request by whether it targets the Central API."""
        if str(request.url).startswith(self._base_url):
            return await self._mock_transport.handle_async_request(request)
        return await self._network_transport.handle_async_request(request)

    async def aclose(self) -> None:
        """Close the transport used for the requests that aren't mocked."""
        await self._network_transport.aclose()


@asynccontextmanager
async def get_mocked_httpx_client(
    *, config: HttpClientConfig, central_api: CentralApiMock, passthrough: bool = False
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Like `get_configured_httpx_client`, but Central API calls go to `central_api`.

    Other requests raise, unless `passthrough` lets them reach the S3 testcontainer.
    """
    base_transport: httpx2.AsyncBaseTransport = central_api.as_transport()
    if passthrough:
        base_transport = _CentralApiRoutingTransport(
            mock_transport=central_api.as_transport(),
            base_url=str(central_api.base_url),
        )
    async with get_configured_httpx_client(
        config=config, base_transport=base_transport
    ) as client:
        yield client
