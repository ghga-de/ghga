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

"""Provides an httpx2.AsyncTransport that paces requests and handles 429 responses."""

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
    """Read one Retry-After value as seconds to wait.

    RFC 9110 allows either seconds or an HTTP date. Anything else returns None.
    """
    value = value.strip()

    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        # inf and nan would end up in a sleep call.
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
    """Seconds a 429 asks the client to wait, or 0.0 if it does not usably say.

    Retry-After may appear more than once and the longest wait wins. Values that cannot
    be parsed are skipped.
    """
    waits = [
        seconds
        for key, value in headers.multi_items()
        if key.lower() == "retry-after"
        and (seconds := _parse_retry_after(value)) is not None
    ]
    return max(waits, default=0.0)


class RateBudget:
    """Request pacing shared by every route of one client.

    Requests take a slot and wait for it, so they spread out instead of all going at
    once. A 429 pushes a shared floor forward; the floor never moves back, so a later
    success cannot cancel the penalty.
    """

    def __init__(self, config: RateLimitingTransportConfig) -> None:
        self._lock = asyncio.Lock()
        self._interval = config.min_request_interval
        self._jitter = config.per_request_jitter
        self._next_slot = 0.0
        self._floor = 0.0

    def _spacing(self) -> float:
        """How far apart two slots are. With no interval, the jitter alone spreads them."""
        return self._interval + random.uniform(0, self._jitter)  # noqa: S311

    async def acquire(self) -> None:
        """Wait until this request may go out."""
        while True:
            async with self._lock:
                now = time.monotonic()
                start_at = max(now, self._next_slot, self._floor)
                self._next_slot = start_at + self._spacing()
                delay = start_at - now
            if delay > 0:
                log.debug("Waiting %.3f s for the next slot.", delay)
                await asyncio.sleep(delay)
            async with self._lock:
                # Go round again only if a 429 moved the floor past our slot.
                if time.monotonic() >= self._floor:
                    return

    async def penalize(self, retry_after: float) -> None:
        """Hold every route back until the server's Retry-After has passed."""
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
        *,
        budget: RateBudget | None = None,
    ) -> None:
        self._budget = budget if budget is not None else RateBudget(config)
        self._transport = transport

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Wait for a slot, then delegate. A 429 holds the whole budget back."""
        await self._budget.acquire()
        # Pass positionally: Otel's httpx instrumentation reads args[0].
        response = await self._transport.handle_async_request(request)
        if response.status_code == 429 and (
            retry_after := _retry_after_seconds(response.headers)
        ):
            await self._budget.penalize(retry_after)
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
