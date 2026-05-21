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

"""HTTP request logic"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from ghga_service_commons.transports import (
    CompositeCacheConfig,
    CompositeTransportFactory,
    ratelimiting_retry_proxies,
)
from pydantic import Field

__all__ = ["HttpClientConfig", "get_configured_httpx_client"]


class HttpClientConfig(CompositeCacheConfig):
    """Configuration for HTTP Client functionality in the DHFS"""

    http_request_timeout_seconds: float = Field(
        default=60.0, description="Request timeout setting in seconds."
    )


@asynccontextmanager
async def get_configured_httpx_client(
    *, config: HttpClientConfig
) -> AsyncGenerator[httpx.AsyncClient]:
    """Produce an httpx AsyncClient with configured rate limiting behavior"""
    transport = CompositeTransportFactory.create_ratelimiting_retry_transport(
        config=config
    )
    proxies = ratelimiting_retry_proxies(config=config)
    async with httpx.AsyncClient(
        timeout=config.http_request_timeout_seconds, transport=transport, mounts=proxies
    ) as client:
        yield client
