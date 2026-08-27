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

"""A mock of the GHGA Central API, built on the service commons `ApiMock`."""

__all__ = [
    "CentralApiMock",
    "capture",
    "get_mocked_httpx_client",
]

import json
from collections.abc import AsyncGenerator
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
from ghga_service_commons.api.mock_api import (
    ApiMock,
    ResponseHandler,
    RoutingTransport,
    endpoint,
    respond,
)


def capture(
    received: list, status_code: int = 201, response_json: Any = None
) -> ResponseHandler:
    """Make a handler that records each request's JSON body into `received`."""

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Record the request body and answer with the canned response."""
        received.append(json.loads(request.content))
        return httpx2.Response(status_code=status_code, json=response_json or {})

    return handler


class CentralApiMock(ApiMock):
    """A mock of the GHGA Central API endpoints that the DHFS talks to.

    Each endpoint answers with the handler assigned to `on_fetch_new_uploads`,
    `on_get_removable_files` or `on_submit_report`. Tests can swap those out with
    `respond(...)`, `fail_to_connect(...)` or any other callable taking the request.
    Every request that reaches the mock is recorded in `requests`.

    The transport returned by `as_transport()` answers *every* request, so a test using
    it cannot accidentally reach the network. Where the same client also has to carry
    real traffic - the S3 testcontainer, in practice - `get_mocked_httpx_client` can be
    asked to let that traffic pass through instead.
    """

    on_fetch_new_uploads = endpoint("GET", UPLOADS_PATH, respond(200, json=[]))
    on_get_removable_files = endpoint(
        "POST", REMOVABLE_FILES_PATH, respond(200, json=[])
    )
    on_submit_report = endpoint(
        "POST", INTERROGATION_REPORTS_PATH, respond(201, json={})
    )

    def __init__(self, *, config: CentralClientConfig) -> None:
        """Serve the Central API where the given config expects it."""
        super().__init__(base_url=str(config.central_api_url))


@asynccontextmanager
async def get_mocked_httpx_client(
    *, config: HttpClientConfig, central_api: CentralApiMock, passthrough: bool = False
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Answer Central API calls with `central_api` instead of the network.

    A drop-in for `get_configured_httpx_client`. Requests to anything but the Central
    API raise, unless `passthrough` is set, in which case they are sent over the network
    as usual - which is what a test talking to the S3 testcontainer through the same
    client needs.
    """
    transport: httpx2.AsyncBaseTransport = central_api.as_transport()
    if passthrough:
        transport = RoutingTransport(central_api, fallback=httpx2.AsyncHTTPTransport())
    async with get_configured_httpx_client(
        config=config, base_transport=transport
    ) as client:
        yield client
