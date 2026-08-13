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

import httpx2
from pydantic import Field

from ghga_service_commons.transports import (
    CompositeConfig,
    CompositeTransportFactory,
    ratelimiting_retry_proxies,
)

__all__ = ["HttpClientConfig", "get_configured_httpx_client"]


class HttpClientConfig(CompositeConfig):
    """Configuration for HTTP Client functionality in the DHFS"""

    http_request_timeout_seconds: float = Field(
        default=60.0, description="Request timeout setting in seconds."
    )


@asynccontextmanager
async def get_configured_httpx_client(
    *,
    config: HttpClientConfig,
    base_transport: httpx2.AsyncBaseTransport | None = None,
    mount_env_proxies: bool = True,
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Produce an httpx2 AsyncClient with configured rate limiting behavior

    `base_transport` replaces the network transport at the bottom of the stack. Tests
    use it to route requests to a `MockRouter` while keeping the retry and rate
    limiting layers in place.

    `mount_env_proxies` controls whether proxies from the environment are mounted.
    It cannot be combined with a `base_transport`: mounts take precedence over
    `transport` for every URL they match, env proxies match everything, and each
    proxy mount builds its own network transport. Callers that replace the network
    layer therefore have to pass `False` here to keep their transport reachable.
    """
    if base_transport is not None and mount_env_proxies:
        raise ValueError(
            "`base_transport` would be bypassed by the env proxy mounts; pass"
            " `mount_env_proxies=False` to route all traffic through it."
        )
    transport = CompositeTransportFactory.create_ratelimiting_retry_transport(
        config=config, base_transport=base_transport
    )
    proxies = ratelimiting_retry_proxies(config=config) if mount_env_proxies else {}
    async with httpx2.AsyncClient(
        timeout=config.http_request_timeout_seconds, transport=transport, mounts=proxies
    ) as client:
        yield client
