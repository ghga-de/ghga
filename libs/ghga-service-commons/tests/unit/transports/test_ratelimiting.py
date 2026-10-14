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


"""Tests for the rate limiting transport handling of HTTP 429 responses."""

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
    _scope_of,
)

pytestmark = pytest.mark.asyncio()

_REQUEST = httpx2.Request("GET", "http://test")
_URL = _REQUEST.url

# Pinning the jitter to zero makes the interval the whole spacing, so timing is exact.
_STEP = 0.02


def _budget(**config_kwargs) -> RateBudget:
    """Build a budget, by default paced by a small deterministic interval."""
    config_kwargs.setdefault("min_request_interval", _STEP)
    config_kwargs.setdefault("per_request_jitter", 0.0)
    return RateBudget(RateLimitingTransportConfig(**config_kwargs))


def _unpaced_budget() -> RateBudget:
    """Build a budget that never delays, for tests that only care about floor updates."""
    return _budget(min_request_interval=0.0)


def _mock_transport(responses: list[httpx2.Response]) -> AsyncMock:
    """Build a transport mock returning the given responses in turn."""
    transport = AsyncMock(spec=httpx2.AsyncBaseTransport)
    transport.handle_async_request = AsyncMock(side_effect=responses)
    return transport


def _ratelimiter(
    transport: AsyncMock, budget: RateBudget | None = None, **config_kwargs
) -> AsyncRateLimitingTransport:
    """Wrap the given transport in a rate limiting transport with the given overrides."""
    config_kwargs.setdefault("min_request_interval", 0.0)
    config_kwargs.setdefault("per_request_jitter", 0.0)
    return AsyncRateLimitingTransport(
        config=RateLimitingTransportConfig(**config_kwargs),
        transport=transport,
        budget=budget,
    )


def _remaining_retry_after_wait(budget: RateBudget, url: httpx2.URL = _URL) -> float:
    """Seconds the budget is still holding back the scope of the given URL."""
    return max(0.0, budget._scopes[_scope_of(url)].floor - time.monotonic())


async def _acquired_at(
    budget: RateBudget, started: float, url: httpx2.URL = _URL
) -> float:
    """Acquire a slot and report how far into the run it was granted."""
    await budget.acquire(url)
    return time.monotonic() - started


async def test_concurrent_requests_are_spread_not_released_together():
    """Ensure concurrent callers get successive slots instead of all firing at once."""
    budget = _budget()
    started = time.monotonic()

    grants = await asyncio.gather(*(_acquired_at(budget, started) for _ in range(5)))

    # Ensure spacing between calls is consistent within some tolerance
    assert grants == sorted(grants)
    for earlier, later in pairwise(grants):
        assert later - earlier == pytest.approx(_STEP, abs=_STEP)
    assert grants[-1] >= 4 * _STEP


async def test_no_pacing_configured_grants_immediately():
    """Ensure the gate adds nothing when neither interval nor jitter is configured."""
    budget = _budget(min_request_interval=0.0)
    started = time.monotonic()

    await asyncio.gather(*(_acquired_at(budget, started) for _ in range(5)))

    assert time.monotonic() - started < _STEP


async def test_default_config_alone_spreads_requests():
    """Ensure the defaults alone spread requests, guarding the jitter default."""
    budget = RateBudget(RateLimitingTransportConfig())
    started = time.monotonic()

    grants = await asyncio.gather(*(_acquired_at(budget, started) for _ in range(8)))

    assert grants == sorted(grants)
    assert grants[-1] > 0.05


async def test_penalty_arriving_mid_wait_requeues_the_waiter():
    """Ensure a request already waiting learns about a 429 that lands while it sleeps."""
    budget = _budget(min_request_interval=0.02)
    await budget.acquire(_URL)  # take the first slot so the next one has to wait

    async def penalize_shortly() -> None:
        await asyncio.sleep(0.01)
        await budget.update_floor(_URL, 0.15)

    started = time.monotonic()
    await asyncio.gather(budget.acquire(_URL), penalize_shortly())

    assert time.monotonic() - started >= 0.15


async def test_penalty_never_moves_backwards():
    """Ensure a smaller floor cannot shorten a longer one that is still in force."""
    budget = _unpaced_budget()

    await budget.update_floor(_URL, 30)
    await budget.update_floor(_URL, 1)

    assert _remaining_retry_after_wait(budget) == pytest.approx(30, abs=1)


async def test_penalty_holds_back_only_its_own_scope():
    """Ensure a 429 from one service leaves the client's other services free."""
    budget = _unpaced_budget()
    await budget.update_floor(httpx2.URL("http://test/upload/a"), 30)

    started = time.monotonic()
    await budget.acquire(httpx2.URL("http://test/download/b"))

    assert time.monotonic() - started < _STEP
    held = httpx2.URL("http://test/upload/b")
    assert _remaining_retry_after_wait(budget, held) == pytest.approx(30, abs=1)


async def test_scopes_are_paced_independently():
    """Ensure pacing spaces requests to one scope but not across scopes."""
    budget = _budget()
    started = time.monotonic()

    first_upload, second_upload, download = await asyncio.gather(
        _acquired_at(budget, started, httpx2.URL("http://test/upload/a")),
        _acquired_at(budget, started, httpx2.URL("http://test/upload/b")),
        _acquired_at(budget, started, httpx2.URL("http://test/download/a")),
    )

    assert second_upload - first_upload >= _STEP * 0.75
    assert download < _STEP * 0.75


@pytest.mark.parametrize(
    "url, scope",
    [
        ("https://H/upload/boxes/1?x=1", "https://h/upload"),
        ("http://u:p@h:8080/x/y", "http://h:8080/x"),
        ("https://h", "https://h/"),
        ("https://h/", "https://h/"),
    ],
)
async def test_scope_is_origin_and_first_path_segment(url: str, scope: str):
    """Ensure a URL is keyed by origin and first path segment, the port only if given."""
    assert _scope_of(httpx2.URL(url)) == scope


async def test_passes_through_non_429_response():
    """Ensure non-429 responses are returned and do not force a wait."""
    response = httpx2.Response(httpx2.codes.OK)
    budget = _unpaced_budget()

    result = await _ratelimiter(
        _mock_transport([response]), budget
    ).handle_async_request(_REQUEST)

    assert result is response
    assert _remaining_retry_after_wait(budget) == 0


async def test_429_with_retry_after_forces_wait():
    """Ensure a 429 with a Retry-After forces a wait."""
    budget = _unpaced_budget()
    response = httpx2.Response(429, headers={"Retry-After": "5"})

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_retry_after_wait(budget) == pytest.approx(5, abs=1)


async def test_429_without_retry_after_leaves_pacing_to_the_retry_layer():
    """Ensure a missing Retry-After header does not add any wait."""
    budget = _unpaced_budget()
    response = httpx2.Response(429)

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_retry_after_wait(budget) == 0


async def test_budget_is_shared_when_injected():
    """Ensure two transports given the same budget actually share it."""
    budget = _budget()
    first = _ratelimiter(_mock_transport([httpx2.Response(200)]), budget)
    second = _ratelimiter(_mock_transport([httpx2.Response(200)]), budget)
    started = time.monotonic()

    await asyncio.gather(
        first.handle_async_request(_REQUEST), second.handle_async_request(_REQUEST)
    )

    assert time.monotonic() - started >= _STEP * 0.75


async def test_transport_builds_its_own_budget_when_none_is_given():
    """Ensure the transport still paces itself when used standalone."""
    ratelimiter = _ratelimiter(_mock_transport([httpx2.Response(200)]))

    await ratelimiter.handle_async_request(_REQUEST)

    assert isinstance(ratelimiter._budget, RateBudget)


async def test_aclose_delegates_to_wrapped_transport():
    """Closing the rate limiting transport closes the transport it wraps."""
    transport = _mock_transport([])

    await _ratelimiter(transport).aclose()

    transport.aclose.assert_awaited_once()


async def test_async_context_manager_closes_transport():
    """Exiting the async context manager closes the wrapped transport."""
    transport = _mock_transport([])

    async with _ratelimiter(transport) as ratelimiter:
        assert isinstance(ratelimiter, AsyncRateLimitingTransport)

    transport.aclose.assert_awaited_once()


async def test_429_with_http_date_retry_after_is_honored():
    """Ensure a Retry-After given as an HTTP date is honored instead of crashing."""
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    response = httpx2.Response(
        429, headers={"Retry-After": format_datetime(retry_at, usegmt=True)}
    )
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_retry_after_wait(budget) == pytest.approx(30, abs=2)


async def test_429_with_past_http_date_does_not_wait():
    """Ensure a Retry-After date that has already passed asks for no wait at all."""
    retry_at = datetime.now(timezone.utc) - timedelta(seconds=30)
    response = httpx2.Response(
        429, headers={"Retry-After": format_datetime(retry_at, usegmt=True)}
    )
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_retry_after_wait(budget) == 0


@pytest.mark.parametrize("value", ["garbage", "", "inf", "nan"])
async def test_429_with_unusable_retry_after_is_treated_as_absent(value: str):
    """Ensure unparsable and non-finite values are ignored rather than reaching the sleep."""
    response = httpx2.Response(429, headers={"Retry-After": value})
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_retry_after_wait(budget) == 0


async def test_429_with_repeated_retry_after_takes_the_longest():
    """Ensure repeated Retry-After headers resolve to the longest wait, not to header order."""
    response = httpx2.Response(
        429, headers=[("Retry-After", "120"), ("Retry-After", "5")]
    )
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_retry_after_wait(budget) == pytest.approx(120, abs=1)


async def test_429_with_repeated_retry_after_ignores_unusable_values():
    """Ensure a malformed duplicate cannot suppress a usable sibling."""
    response = httpx2.Response(
        429, headers=[("Retry-After", "garbage"), ("Retry-After", "45")]
    )
    budget = _unpaced_budget()

    await _ratelimiter(_mock_transport([response]), budget).handle_async_request(
        _REQUEST
    )

    assert _remaining_retry_after_wait(budget) == pytest.approx(45, abs=1)
