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


"""Tests for the request pacing budget and the transport that drives it."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from itertools import pairwise
from unittest.mock import AsyncMock

import httpx2
import pytest

from ghga_service_commons.transports.config import RateLimitingTransportConfig
from ghga_service_commons.transports.ratelimiting import (
    AsyncRateLimitingTransport,
    RateBudget,
)

_REQUEST = httpx2.Request("GET", "http://test")

# Pinning the jitter to zero makes the interval the whole spacing, so timing is exact.
_STEP = 0.02


def _budget(**config_kwargs) -> RateBudget:
    """Build a budget, by default paced by a small deterministic interval."""
    config_kwargs.setdefault("min_request_interval", _STEP)
    config_kwargs.setdefault("per_request_jitter", 0.0)
    return RateBudget(RateLimitingTransportConfig(**config_kwargs))


def _unpaced_budget() -> RateBudget:
    """Build a budget that never delays, for tests that only care about penalties."""
    return _budget(min_request_interval=0.0)


def _mock_transport(responses: list[httpx2.Response]) -> AsyncMock:
    """Build a transport mock returning the given responses in turn."""
    transport = AsyncMock(spec=httpx2.AsyncBaseTransport)
    transport.handle_async_request = AsyncMock(side_effect=responses)
    return transport


def _ratelimiter(
    transport: AsyncMock, budget: RateBudget | None = None, **config_kwargs
) -> AsyncRateLimitingTransport:
    """Wrap the transport in a rate limiting transport with the given overrides."""
    config_kwargs.setdefault("min_request_interval", 0.0)
    config_kwargs.setdefault("per_request_jitter", 0.0)
    return AsyncRateLimitingTransport(
        config=RateLimitingTransportConfig(**config_kwargs),
        transport=transport,
        budget=budget,
    )


def _remaining_penalty(budget: RateBudget) -> float:
    """Seconds the budget is still holding every route back."""
    return max(0.0, budget._floor - time.monotonic())


async def _acquire_at(budget: RateBudget, started: float) -> float:
    """Acquire a slot and report how far into the run it was granted."""
    await budget.acquire()
    return time.monotonic() - started


# ---------------------------------------------------------------- budget pacing


@pytest.mark.asyncio
async def test_concurrent_requests_are_spread_not_released_together():
    """Concurrent callers get successive slots instead of all firing at once."""
    budget = _budget()
    started = time.monotonic()

    grants = await asyncio.gather(*(_acquire_at(budget, started) for _ in range(5)))

    assert grants == sorted(grants)
    for earlier, later in pairwise(grants):
        assert later - earlier == pytest.approx(_STEP, abs=_STEP)
    assert grants[-1] >= 4 * _STEP * 0.75


@pytest.mark.asyncio
async def test_no_pacing_configured_grants_immediately():
    """With no interval and no jitter the gate adds nothing."""
    budget = _budget(min_request_interval=0.0)
    started = time.monotonic()

    await asyncio.gather(*(_acquire_at(budget, started) for _ in range(5)))

    assert time.monotonic() - started < _STEP


@pytest.mark.asyncio
async def test_default_config_alone_spreads_requests():
    """The defaults spread requests unconfigured; guards the jitter default."""
    budget = RateBudget(RateLimitingTransportConfig())
    started = time.monotonic()

    grants = await asyncio.gather(*(_acquire_at(budget, started) for _ in range(8)))

    assert grants == sorted(grants)
    assert grants[-1] > 0.05


# ------------------------------------------------------------- budget penalties


@pytest.mark.asyncio
async def test_penalty_holds_the_whole_budget_back():
    """A penalty delays the next slot on every route, not just the throttled one."""
    budget = _unpaced_budget()
    await budget.penalize(0.05)
    started = time.monotonic()

    await budget.acquire()

    assert time.monotonic() - started == pytest.approx(0.05, abs=0.05)


@pytest.mark.asyncio
async def test_penalty_arriving_mid_wait_requeues_the_waiter():
    """A request already waiting learns about a 429 that lands while it sleeps."""
    budget = _budget(min_request_interval=0.02)
    await budget.acquire()  # take the first slot so the next one has to wait

    async def penalize_shortly() -> None:
        await asyncio.sleep(0.01)
        await budget.penalize(0.15)

    started = time.monotonic()
    await asyncio.gather(budget.acquire(), penalize_shortly())

    assert time.monotonic() - started >= 0.15


@pytest.mark.asyncio
async def test_penalty_never_moves_backwards():
    """A shorter penalty cannot shorten a longer one that is still in force."""
    budget = _unpaced_budget()

    await budget.penalize(30)
    await budget.penalize(1)

    assert _remaining_penalty(budget) == pytest.approx(30, abs=1)


# ------------------------------------------------------- transport wiring to it


@pytest.mark.asyncio
async def test_passes_through_non_429_response():
    """Non-429 responses are returned unchanged and penalize nothing."""
    response = httpx2.Response(httpx2.codes.OK)
    budget = _unpaced_budget()

    result = await _ratelimiter(
        _mock_transport([response]), budget
    ).handle_async_request(_REQUEST)

    assert result is response
    assert _remaining_penalty(budget) == 0


@pytest.mark.asyncio
async def test_429_with_retry_after_penalizes_the_budget():
    """A 429 with a Retry-After holds the budget back for that long."""
    budget = _unpaced_budget()
    response = httpx2.Response(429, headers={"Retry-After": "5"})

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_penalty(budget) == pytest.approx(5, abs=1)


@pytest.mark.asyncio
async def test_429_without_retry_after_leaves_pacing_to_the_retry_layer():
    """Without a usable Retry-After the budget is not held back; the retry layer waits."""
    budget = _unpaced_budget()
    response = httpx2.Response(429)

    result = await _ratelimiter(
        _mock_transport([response]), budget
    ).handle_async_request(_REQUEST)

    assert _remaining_penalty(budget) == 0
    assert "Should-Wait" not in result.headers


@pytest.mark.asyncio
async def test_budget_is_shared_when_injected():
    """Two transports given the same budget pace against each other."""
    budget = _budget()
    first = _ratelimiter(_mock_transport([httpx2.Response(200)]), budget)
    second = _ratelimiter(_mock_transport([httpx2.Response(200)]), budget)
    started = time.monotonic()

    await asyncio.gather(
        first.handle_async_request(_REQUEST), second.handle_async_request(_REQUEST)
    )

    assert time.monotonic() - started >= _STEP * 0.75


@pytest.mark.asyncio
async def test_transport_builds_its_own_budget_when_none_is_given():
    """Used standalone, the transport still paces itself."""
    ratelimiter = _ratelimiter(_mock_transport([httpx2.Response(200)]))

    await ratelimiter.handle_async_request(_REQUEST)

    assert isinstance(ratelimiter._budget, RateBudget)


@pytest.mark.asyncio
async def test_aclose_delegates_to_wrapped_transport():
    """Closing the rate limiting transport closes the transport it wraps."""
    transport = _mock_transport([])

    await _ratelimiter(transport).aclose()

    transport.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_context_manager_closes_transport():
    """Exiting the async context manager closes the wrapped transport."""
    transport = _mock_transport([])

    async with _ratelimiter(transport) as ratelimiter:
        assert isinstance(ratelimiter, AsyncRateLimitingTransport)

    transport.aclose.assert_awaited_once()


# ------------------------------------------------------ Retry-After parsing (C1/C3)


@pytest.mark.asyncio
async def test_429_with_http_date_retry_after_is_honored():
    """RFC 9110 allows an HTTP date instead of seconds, so it has to parse."""
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    response = httpx2.Response(
        429, headers={"Retry-After": format_datetime(retry_at, usegmt=True)}
    )
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_penalty(budget) == pytest.approx(30, abs=2)


@pytest.mark.asyncio
async def test_429_with_past_http_date_does_not_wait():
    """A Retry-After date already in the past asks for no wait at all."""
    retry_at = datetime.now(timezone.utc) - timedelta(seconds=30)
    response = httpx2.Response(
        429, headers={"Retry-After": format_datetime(retry_at, usegmt=True)}
    )
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_penalty(budget) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["garbage", "", "inf", "nan"])
async def test_429_with_unusable_retry_after_is_treated_as_absent(value: str):
    """Unparsable and non-finite values are ignored rather than reaching the sleep."""
    response = httpx2.Response(429, headers={"Retry-After": value})
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_penalty(budget) == 0


@pytest.mark.asyncio
async def test_429_with_repeated_retry_after_takes_the_longest():
    """Repeated headers are read individually and the longest wait wins."""
    response = httpx2.Response(
        429, headers=[("Retry-After", "120"), ("Retry-After", "5")]
    )
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_penalty(budget) == pytest.approx(120, abs=1)


@pytest.mark.asyncio
async def test_429_with_repeated_retry_after_ignores_unusable_values():
    """A malformed duplicate cannot suppress a usable sibling."""
    response = httpx2.Response(
        429, headers=[("Retry-After", "garbage"), ("Retry-After", "45")]
    )
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_penalty(budget) == pytest.approx(45, abs=1)
