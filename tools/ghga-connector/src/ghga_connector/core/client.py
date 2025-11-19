# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Handling session initialization for httpx"""

from contextlib import asynccontextmanager

import hishel
import httpx
from ghga_service_commons.http.correlation import attach_correlation_id_to_requests
from ghga_service_commons.transports import CompositeTransportFactory

from ghga_connector.config import get_config
from ghga_connector.constants import TIMEOUT


def get_cache_transport(
    base_transport: httpx.AsyncBaseTransport | None = None,
    limits: httpx.Limits | None = None,
) -> hishel.AsyncCacheTransport:
    """Construct an async cache transport with `hishel`.

    The `wrapped_transport` parameter can be used for testing to inject, for example,
    an httpx.ASGITransport pointing to a FastAPI app.
    """
    return CompositeTransportFactory.create_cached_ratelimiting_retry_transport(
        get_config(), base_transport=base_transport, limits=limits
    )


def get_mounts(
    base_transport: httpx.AsyncHTTPTransport | None = None,
    limits: httpx.Limits | None = None,
) -> dict[str, httpx.AsyncBaseTransport]:
    """Return a dict of mounts for the cache transport."""
    return {
        "all://": get_cache_transport(base_transport=base_transport, limits=limits),
    }


@asynccontextmanager
async def async_client():
    """Yields a context manager async httpx client and closes it afterward"""
    config = get_config()
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        mounts=get_mounts(
            limits=httpx.Limits(
                max_connections=config.max_concurrent_downloads,
                max_keepalive_connections=config.max_concurrent_downloads,
            )
        ),
    ) as client:
        attach_correlation_id_to_requests(client)
        yield client
