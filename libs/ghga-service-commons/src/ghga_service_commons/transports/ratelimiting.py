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

"""Provides an httpx2.AsyncTransport that handles rate limiting responses."""

import asyncio
import math
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from logging import getLogger
from types import TracebackType

import httpx2

from ghga_service_commons.transports.config import RateLimitingTransportConfig

log = getLogger(__name__)


def _parse_retry_after(value: str) -> float | None:
    """Turn a single Retry-After value into a number of seconds to wait.

    RFC 9110 allows the header to carry either a number of seconds or an HTTP date, so
    both forms are accepted. Returns None when the value is neither, which lets the
    caller treat the header as if it had not been sent instead of failing the request.
    """
    value = value.strip()

    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        # Reject inf and nan, which would otherwise be carried into the sleep below.
        return max(0.0, seconds) if math.isfinite(seconds) else None

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        # HTTP dates are GMT; a value parsed without a zone would compare wrong.
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def _retry_after_seconds(headers: httpx2.Headers) -> float:
    """Determine how long a 429 response asks the client to wait.

    A response may carry Retry-After more than once. `headers.items()` joins repeats
    into one comma separated string that parses as neither allowed form, so the
    individual values are read instead and the longest wait wins. Values that cannot be
    parsed are skipped; 0.0 means no usable Retry-After was found.
    """
    waits = [
        seconds
        for key, value in headers.multi_items()
        if key.lower() == "retry-after"
        and (seconds := _parse_retry_after(value)) is not None
    ]
    return max(waits, default=0.0)


class AsyncRateLimitingTransport(httpx2.AsyncBaseTransport):
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
        self, config: RateLimitingTransportConfig, transport: httpx2.AsyncBaseTransport
    ) -> None:
        self._jitter = config.per_request_jitter
        self._transport = transport
        self._num_requests = 0
        self._reset_after: int = config.retry_after_applicable_for_num_requests
        self._last_retry_after_received: float = 0
        self._wait_time: float = 0

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
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
        # Strictly pass request as non kwarg arg to work around Otel httpx
        # instrumentation trying to extract from arg[0]
        response = await self._transport.handle_async_request(request)

        # Update state
        self._num_requests += 1
        if response.status_code == 429:
            retry_after = _retry_after_seconds(response.headers)
            if retry_after:
                self._wait_time = retry_after
                log.info("Received retry after response: %.3f s.", self._wait_time)
                self._last_retry_after_received = time.monotonic()
            else:
                log.warning(
                    "No usable Retry-After header in 429 response.\nDelegating to underlying wait strategy."
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
