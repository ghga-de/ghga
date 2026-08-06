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
from ghga_service_commons.transports import (
    CompositeConfig,
    CompositeTransportFactory,
    ratelimiting_retry_proxies,
)
from pydantic import Field
from tenacity import RetryError

from dhfs import __version__

__all__ = [
    "ConnectionFailedError",
    "HttpClientConfig",
    "RequestFailedError",
    "check_for_request_errors",
    "get_configured_httpx_client",
    "raise_if_connection_failed",
]

USER_AGENT = f"GHGA DataHubFileService/{__version__}"


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
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Produce an httpx2 AsyncClient with configured rate limiting behavior

    `base_transport` replaces the innermost transport that actually performs the
    request. It is meant for tests, which can supply a mock transport that still
    gets exercised through the rate limiting and retry layers.
    """
    transport = CompositeTransportFactory.create_ratelimiting_retry_transport(
        config=config, base_transport=base_transport
    )
    headers = httpx2.Headers({"User-Agent": USER_AGENT})
    proxies = ratelimiting_retry_proxies(config=config)
    async with httpx2.AsyncClient(
        timeout=config.http_request_timeout_seconds,
        headers=headers,
        transport=transport,
        mounts=proxies,
    ) as client:
        yield client


class RequestFailedError(RuntimeError):
    """Thrown when a request fails without returning a response code"""

    def __init__(self, *, url: str):
        message = f"The request to '{url}' failed."
        super().__init__(message)


class ConnectionFailedError(RuntimeError):
    """Thrown when a ConnectError or ConnectTimeout error is raised by httpx2"""

    def __init__(self, *, url: str, reason: str):
        message = f"Request to '{url}' failed to connect. Reason: {reason}"
        super().__init__(message)


def raise_if_connection_failed(request_error: httpx2.RequestError, url: str):
    """Check if request exception is caused by hitting max retries and raise accordingly"""
    if isinstance(request_error, (httpx2.ConnectError, httpx2.ConnectTimeout)):
        connection_failure = str(request_error.args[0])
        raise ConnectionFailedError(url=url, reason=connection_failure)


def check_for_request_errors(retry_error: RetryError, url: str):
    """Examine an instance of a RetryError to see if it contains an httpx2.RequestError

    Raises a ConnectionFailedError if there's a ConnectError or ConnectTimeout, and
    re-raises all other httpx2.RequestError types as a RequestFailedError.
    """
    exception = retry_error.last_attempt.exception()
    if exception and isinstance(exception, httpx2.RequestError):
        raise_if_connection_failed(request_error=exception, url=url)
        raise RequestFailedError(url=url) from retry_error
