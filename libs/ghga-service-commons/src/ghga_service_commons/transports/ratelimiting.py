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

"""Provides an httpx.AsyncTransport that handles rate limiting responses."""

import asyncio
import random
import time
from logging import getLogger
from types import TracebackType

import httpx

from ghga_service_commons.transports.config import RateLimitingTransportConfig

log = getLogger(__name__)


class AsyncRateLimitingTransport(httpx.AsyncBaseTransport):
    """Custom async Transport adding rate limiting handling on top of AsyncHTTPTransport.

    If no retry-after header is found in the 429 response, this hands control back to the
    caller and populates a `Should-Wait` header to signal that a custom wait/retry strategy
    is needed.
    Can be configured to add some jitter in between requests and carry over the wait time
    of a 429 retry-after response for a configurable number of requests.
    Both can be helpful in a situation when concurrent requests are fired in rapid succession
    and might overwhelm the request endpoint.
    """

    def __init__(
        self, config: RateLimitingTransportConfig, transport: httpx.AsyncBaseTransport
    ) -> None:
        self._jitter = config.per_request_jitter
        self._transport = transport
        self._num_requests = 0
        self._reset_after: int = config.retry_after_applicable_for_num_requests
        self._last_retry_after_received: float = 0
        self._wait_time: float = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handles HTTP requests and adds wait logic for HTTP 429 responses around calls."""
        # Calculate seconds since the last request has been fired and corresponding wait time
        time_elapsed = time.monotonic() - self._last_retry_after_received
        remaining_wait = max(0, self._wait_time - time_elapsed)
        log.debug(
            "Time elapsed since last request: %.3f s.\nRemaining wait time: %.3f s.",
            time_elapsed,
            remaining_wait,
        )

        # Add jitter to both cases and sleep
        if remaining_wait < self._jitter:
            sleep_for = random.uniform(remaining_wait, self._jitter)  # noqa: S311
            log.debug("Sleeping for %.3f s.", sleep_for)
            await asyncio.sleep(sleep_for)
        else:
            sleep_for = random.uniform(remaining_wait, remaining_wait + self._jitter)  # noqa: S311
            log.debug("Sleeping for %.3f s.", sleep_for)
            await asyncio.sleep(sleep_for)

        # Delegate call and update timestamp
        response = await self._transport.handle_async_request(request=request)

        # Update state
        self._num_requests += 1
        if response.status_code == 429:
            retry_after = 0.0
            for k, v in response.headers.items():
                if k.lower() == "retry-after":
                    retry_after = float(v)
            if retry_after:
                self._wait_time = retry_after
                log.info("Received retry after response: %.3f s.", self._wait_time)
                self._last_retry_after_received = time.monotonic()
            else:
                log.warning(
                    "Retry-After header not present in 429 response.\nDelegating to underlying wait strategy."
                )
                # Modify response headers to communicate intent to retry layer
                response.headers["Should-Wait"] = "true"
            self._num_requests = 0
        elif self._reset_after and self._reset_after <= self._num_requests:
            self._wait_time = 0
            self._num_requests = 0

        return response

    async def aclose(self) -> None:  # noqa: D102
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncRateLimitingTransport":  # noqa: D105
        return self

    async def __aexit__(  # noqa: D105
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self.aclose()
