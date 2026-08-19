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
from ghga_connector.constants import KEEPALIVE_EXPIRY, TIMEOUT
from ghga_service_commons.http.correlation import attach_correlation_id_to_requests
from ghga_service_commons.transports import (
    AsyncRetryTransport,
    CompositeTransportFactory,
    ratelimiting_retry_proxies,
)


def get_ratelimiting_retry_transport(
    base_transport: httpx2.AsyncBaseTransport | None = None,
    limits: httpx2.Limits | None = None,
) -> AsyncRetryTransport:
    """Construct an async rate-limiting retry transport.

    The `base_transport` parameter can be used for testing to inject, for example,
    an httpx2.ASGITransport pointing to a FastAPI app.
    """
    return CompositeTransportFactory.create_ratelimiting_retry_transport(
        get_config(), base_transport=base_transport, limits=limits
    )


@asynccontextmanager
async def async_client(*, purpose: Literal["upload", "download"]):
    """Yields a context manager async httpx2 client and closes it afterward.

    `purpose` selects which of the two part-concurrency settings sizes the connection
    pool, since a given client is only ever used for one of the two transfer paths.
    """
    config = get_config()
    # httpx2 applies `max_connections` across all origins rather than per host, so the
    # pool is sized from the number of parts that can be in flight at once. A short
    # `keepalive_expiry` keeps idle connections from lingering long enough for the
    # server to reap them first.
    max_concurrent_parts = (
        config.max_concurrent_uploads
        if purpose == "upload"
        else config.max_concurrent_downloads
    )
    limits = httpx2.Limits(
        max_connections=max_concurrent_parts,
        max_keepalive_connections=max_concurrent_parts,
        keepalive_expiry=KEEPALIVE_EXPIRY,
    )
    transport = get_ratelimiting_retry_transport(limits=limits)
    proxies = ratelimiting_retry_proxies(config=config, limits=limits)
    async with httpx2.AsyncClient(
        timeout=TIMEOUT, transport=transport, mounts=proxies
    ) as client:
        attach_correlation_id_to_requests(client)
        yield client
