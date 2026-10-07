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
    AsyncRetryTransport,
    BaseTransportFactory,
    CompositeTransportFactory,
    default_base_transport_factory,
    ratelimiting_retry_proxies,
)


def get_ratelimiting_retry_transport(
    make_base_transport: BaseTransportFactory | None = None,
) -> AsyncRetryTransport:
    """Construct an async rate-limiting retry transport.

    The `make_base_transport` parameter can be used for testing to inject, for example,
    an httpx2.ASGITransport pointing to a FastAPI app.
    """
    return CompositeTransportFactory.create_ratelimiting_retry_transport(
        get_config(), make_base_transport=make_base_transport
    )


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
    make_base_transport = default_base_transport_factory(limits)
    transport = get_ratelimiting_retry_transport(make_base_transport)
    proxies = ratelimiting_retry_proxies(
        config=config, make_base_transport=make_base_transport
    )
    async with httpx2.AsyncClient(
        timeout=TIMEOUT, transport=transport, mounts=proxies
    ) as client:
        attach_correlation_id_to_requests(client)
        yield client
