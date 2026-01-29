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

"""HTTP request logic"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from ghga_service_commons.transports import (
    CompositeCacheConfig,
    CompositeTransportFactory,
    ratelimiting_retry_proxies,
)
from tenacity import RetryError

from dhfs.constants import HTTPX_TIMEOUT

__all__ = [
    "ConnectionFailedError",
    "RequestFailedError",
    "check_for_request_errors",
    "get_configured_httpx_client",
    "raise_if_connection_failed",
]


@asynccontextmanager
async def get_configured_httpx_client(
    *, config: CompositeCacheConfig
) -> AsyncGenerator[httpx.AsyncClient]:
    """Produce an httpx AsyncClient with configured rate limiting behavior"""
    transport = CompositeTransportFactory.create_ratelimiting_retry_transport(
        config=config
    )
    proxies = ratelimiting_retry_proxies(config=config)
    async with httpx.AsyncClient(
        timeout=HTTPX_TIMEOUT, transport=transport, mounts=proxies
    ) as client:
        yield client


class RequestFailedError(RuntimeError):
    """Thrown when a request fails without returning a response code"""

    def __init__(self, *, url: str):
        message = f"The request to '{url}' failed."
        super().__init__(message)


class ConnectionFailedError(RuntimeError):
    """Thrown when a ConnectError or ConnectTimeout error is raised by httpx"""

    def __init__(self, *, url: str, reason: str):
        message = f"Request to '{url}' failed to connect. Reason: {reason}"
        super().__init__(message)


def raise_if_connection_failed(request_error: httpx.RequestError, url: str):
    """Check if request exception is caused by hitting max retries and raise accordingly"""
    if isinstance(request_error, (httpx.ConnectError, httpx.ConnectTimeout)):
        connection_failure = str(request_error.args[0])
        raise ConnectionFailedError(url=url, reason=connection_failure)


def check_for_request_errors(retry_error: RetryError, url: str):
    """Examine an instance of a RetryError to see if it contains an httpx.RequestError

    Raises a ConnectionFailedError if there's a ConnectError or ConnectTimeout, and
    re-raises all other httpx.RequestError types as a RequestFailedError.
    """
    exception = retry_error.last_attempt.exception()
    if exception and isinstance(exception, httpx.RequestError):
        raise_if_connection_failed(request_error=exception, url=url)
        raise RequestFailedError(url=url) from retry_error
