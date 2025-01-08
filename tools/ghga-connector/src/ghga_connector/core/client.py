# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from contextlib import asynccontextmanager, contextmanager
from functools import cached_property
from typing import Union

import hishel
import httpx
from ghga_service_commons.http.correlation import attach_correlation_id_to_requests
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential_jitter,
)

from ghga_connector.config import CONFIG
from ghga_connector.constants import TIMEOUT


class HttpxClientConfigurator:
    """Helper class to make max_retries user configurable"""

    @cached_property
    def retry_handler(self):
        """Configure client retry handler with exponential backoff"""
        return AsyncRetrying(
            reraise=True,
            retry=(
                retry_if_exception_type(
                    (
                        httpx.ConnectError,
                        httpx.ConnectTimeout,
                        httpx.TimeoutException,
                    )
                )
                | retry_if_result(
                    lambda response: response.status_code in CONFIG.retry_status_codes
                )
            ),
            stop=stop_after_attempt(CONFIG.max_retries),
            wait=wait_exponential_jitter(max=CONFIG.exponential_backoff_max),
        )


retry_handler = HttpxClientConfigurator().retry_handler


@contextmanager
def httpx_client():
    """Yields a context manager httpx client and closes it afterward"""
    with httpx.Client(
        timeout=TIMEOUT,
        limits=httpx.Limits(
            max_connections=CONFIG.max_concurrent_downloads,
            max_keepalive_connections=CONFIG.max_concurrent_downloads,
        ),
    ) as client:
        yield client


def get_cache_transport(
    wrapped_transport: Union[httpx.AsyncBaseTransport, None] = None,
) -> hishel.AsyncCacheTransport:
    """Construct an async cache transport with `hishel`.

    The `wrapped_transport` parameter can be used for testing to inject, for example,
    an httpx.ASGITransport pointing to a FastAPI app.
    """
    cache_transport = hishel.AsyncCacheTransport(
        transport=wrapped_transport or httpx.AsyncHTTPTransport(),
        storage=hishel.AsyncInMemoryStorage(ttl=1800),  # persist for 30 minutes
        controller=hishel.Controller(
            cacheable_methods=["POST", "GET"],
            cacheable_status_codes=[200, 201],
        ),
    )
    return cache_transport


def get_mounts() -> dict[str, httpx.AsyncBaseTransport]:
    """Return a dict of mounts for the cache transport."""
    return {
        "all://": get_cache_transport(),
    }


@asynccontextmanager
async def async_client():
    """Yields a context manager async httpx client and closes it afterward"""
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        limits=httpx.Limits(
            max_connections=CONFIG.max_concurrent_downloads,
            max_keepalive_connections=CONFIG.max_concurrent_downloads,
        ),
        mounts=get_mounts(),
    ) as client:
        attach_correlation_id_to_requests(client)
        yield client
