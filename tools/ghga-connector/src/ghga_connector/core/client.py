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
"""Handling session initialization for httpx2"""

from contextlib import asynccontextmanager
from typing import Literal

import httpx2

from ghga_connector.config import get_config
from ghga_connector.constants import KEEPALIVE_EXPIRY, POOL_HEADROOM, TIMEOUT
from ghga_service_commons.http.correlation import attach_correlation_id_to_requests
from ghga_service_commons.transports import (
    BaseTransportFactory,
    client_routes,
    default_base_transport_factory,
)


class OpenUploadLimitReached(Exception):
    """The Upload API refused a new upload: the box holds the most open uploads it
    accepts.
    """


class OpenUploadLimitTransport(httpx2.AsyncBaseTransport):
    """Turns the Upload API's `tooManyOpenUploads` answer into `OpenUploadLimitReached`.

    It sits below the retry transport, which retries every 429 but no exception of
    this kind. Only an upload that ends frees room, so retries would only delay the
    batch's wait for room.
    """

    def __init__(self, transport: httpx2.AsyncBaseTransport):
        self._transport = transport

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Send the request; raise `OpenUploadLimitReached` for that refusal."""
        response = await self._transport.handle_async_request(request)
        if request.method == "POST" and response.status_code == 429:
            await response.aread()
            try:
                exception_id = response.json().get("exception_id")
            except (ValueError, AttributeError):
                exception_id = None
            if exception_id == "tooManyOpenUploads":
                await response.aclose()
                raise OpenUploadLimitReached()
        return response

    async def aclose(self) -> None:
        """Close the wrapped transport."""
        await self._transport.aclose()


def _with_open_upload_limit(
    make_base_transport: BaseTransportFactory,
) -> BaseTransportFactory:
    """Put an `OpenUploadLimitTransport` on each transport the factory makes."""
    return lambda proxy: OpenUploadLimitTransport(make_base_transport(proxy))


@asynccontextmanager
async def async_client(*, purpose: Literal["upload", "download"]):
    """Yields a context manager async httpx2 client and closes it afterward.

    A client only ever serves one transfer path, so `purpose` picks which of the two
    part-concurrency settings sizes the connection pool.
    """
    config = get_config()
    max_concurrent_parts = (
        config.max_concurrent_uploads
        if purpose == "upload"
        else config.max_concurrent_downloads
    )
    limits = httpx2.Limits(
        max_connections=max_concurrent_parts + POOL_HEADROOM,
        max_keepalive_connections=max_concurrent_parts + POOL_HEADROOM,
        keepalive_expiry=KEEPALIVE_EXPIRY,
    )
    make_base_transport = default_base_transport_factory(limits=limits)
    if purpose == "upload":
        make_base_transport = _with_open_upload_limit(make_base_transport)
    routes = client_routes(config, make_base_transport=make_base_transport)
    async with httpx2.AsyncClient(timeout=TIMEOUT, **routes) as client:
        attach_correlation_id_to_requests(client)
        yield client
