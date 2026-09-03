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
    """Turn a single Retry-After value into a number of seconds to wait

    RFC 9110 allows the header to carry either a number of seconds or an HTTP date, so
    both forms are accepted. Returns None when the value is neither.
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
        # A missing zone would compare wrong.
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def _retry_after_seconds(headers: httpx2.Headers) -> float:
    """Determine how long a 429 response asks the client to wait.

    A response may carry Retry-After more than once and the longest wait wins.
    Values that cannot be parsed are skipped and 0.0 means no usable Retry-After was found.
    """
    waits = [
        seconds
        for key, value in headers.multi_items()
        if key.lower() == "retry-after"
        and (seconds := _parse_retry_after(value)) is not None
    ]
    return max(waits, default=0.0)


class RateBudget:
    """Request pacing budget shared by every route of one client.

    Requests take a slot and wait for it, so they spread out instead of all going at
    once. A 429 pushes a shared floor forward.
    """

    def __init__(self, config: RateLimitingTransportConfig) -> None:
        self._lock = asyncio.Lock()
        self._interval = config.min_request_interval
        self._jitter = config.per_request_jitter
        self._next_slot = 0.0
        self._floor = 0.0

    def _spacing(self) -> float:
        """Compute how far away two slots are."""
        return self._interval + random.uniform(0, self._jitter)  # noqa: S311

    async def acquire(self) -> None:
        """Wait until this request may go out."""
        while True:
            async with self._lock:
                now = time.monotonic()
                current_slot = max(now, self._next_slot, self._floor)
                self._next_slot = current_slot + self._spacing()
                delay = current_slot - now
            if delay > 0:
                log.debug("Waiting %.3f s for the next slot.", delay)
                await asyncio.sleep(delay)
            async with self._lock:
                # If a Retry-After moved the floor beyond the current slot
                # in the meantime, do an extra round to get a new slot
                if time.monotonic() >= self._floor:
                    return

    async def update_floor(self, retry_after: float) -> None:
        """Update the Retry-After floor."""
        async with self._lock:
            self._floor = max(self._floor, time.monotonic() + retry_after)
        log.info("Received retry after response: %.3f s.", retry_after)


class AsyncRateLimitingTransport(httpx2.AsyncBaseTransport):
    """Paces requests and honors Retry-After on 429 responses.

    Pass a `RateBudget` to share pacing with the other transports of the same client.
    Without one, this transport paces itself alone.
    """

    def __init__(
        self,
        config: RateLimitingTransportConfig,
        transport: httpx2.AsyncBaseTransport,
        budget: RateBudget | None = None,
    ) -> None:
        self._budget = budget if budget is not None else RateBudget(config)
        self._transport = transport

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Wait for a slot, then delegate. A 429 holds the whole budget back."""
        await self._budget.acquire()
        # Strictly pass request as non kwarg arg to work around Otel httpx
        # instrumentation trying to extract from arg[0]
        response = await self._transport.handle_async_request(request)
        if response.status_code == 429 and (
            retry_after := _retry_after_seconds(response.headers)
        ):
            await self._budget.update_floor(retry_after)
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
