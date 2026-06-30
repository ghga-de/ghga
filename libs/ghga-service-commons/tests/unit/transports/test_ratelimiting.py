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

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from ghga_service_commons.transports.config import RateLimitingTransportConfig
from ghga_service_commons.transports.ratelimiting import AsyncRateLimitingTransport

# The per-request sleep is drawn from random.uniform keeps the real sleep at zero
# while exposing the delay the transport computed.
UNIFORM = "ghga_service_commons.transports.ratelimiting.random.uniform"
_REQUEST = httpx.Request("GET", "http://test")


def _mock_transport(responses: list[httpx.Response]) -> AsyncMock:
    """Build a transport mock returning the given responses in turn."""
    transport = AsyncMock(spec=httpx.AsyncBaseTransport)
    transport.handle_async_request = AsyncMock(side_effect=responses)
    return transport


def _ratelimiter(transport: AsyncMock, **config_kwargs) -> AsyncRateLimitingTransport:
    """Wrap the transport in a rate limiting transport with the given config overrides."""
    return AsyncRateLimitingTransport(
        config=RateLimitingTransportConfig(**config_kwargs), transport=transport
    )


@pytest.mark.asyncio
async def test_passes_through_non_429_response():
    """Ensure non-429 responses are returned unchanged without a Should-Wait header."""
    response = httpx.Response(httpx.codes.OK)
    ratelimiter = _ratelimiter(_mock_transport([response]))

    result = await ratelimiter.handle_async_request(_REQUEST)

    assert result is response
    assert "Should-Wait" not in result.headers


@pytest.mark.asyncio
async def test_429_with_retry_after_sets_wait_time():
    """Ensure a 429 with a Retry-After header stores the wait time and does not signal Should-Wait."""
    response = httpx.Response(429, headers={"Retry-After": "5"})
    ratelimiter = _ratelimiter(_mock_transport([response]))

    result = await ratelimiter.handle_async_request(_REQUEST)

    assert ratelimiter._wait_time == 5.0
    assert "Should-Wait" not in result.headers


@pytest.mark.asyncio
async def test_429_without_retry_after_sets_should_wait_header():
    """Ensure a 429 without a Retry-After header signals Should-Wait and stores no wait time."""
    response = httpx.Response(429)
    ratelimiter = _ratelimiter(_mock_transport([response]))

    result = await ratelimiter.handle_async_request(_REQUEST)

    assert result.headers["Should-Wait"] == "true"
    assert ratelimiter._wait_time == 0


@pytest.mark.asyncio
async def test_carried_over_wait_time_is_applied_to_next_request():
    """Ensure a wait time learned from a 429 is applied as the delay before the next request."""
    responses = [
        httpx.Response(429, headers={"Retry-After": "10"}),
        httpx.Response(httpx.codes.OK),
    ]
    ratelimiter = _ratelimiter(_mock_transport(responses))

    await ratelimiter.handle_async_request(_REQUEST)

    # Returning 0.0 keeps the real asyncio.sleep instant; the bounds passed to uniform
    # are the computed remaining wait, so the carried-over delay stays observable.
    with patch(UNIFORM, return_value=0.0) as mock_uniform:
        await ratelimiter.handle_async_request(_REQUEST)

    remaining_wait = mock_uniform.call_args.args[0]
    # The second request follows immediately, so almost the full delay still remains.
    assert remaining_wait == pytest.approx(10, abs=0.5)


@pytest.mark.asyncio
async def test_wait_time_reset_after_configured_requests():
    """Ensure stored wait time is cleared once the configured number of requests has passed."""
    ratelimiter = _ratelimiter(
        _mock_transport([httpx.Response(httpx.codes.OK)] * 2),
        retry_after_applicable_for_num_requests=2,
    )
    # Simulate a wait time still in effect from a previous Retry-After response.
    ratelimiter._wait_time = 5.0

    await ratelimiter.handle_async_request(_REQUEST)
    # The first request only counts towards the reset threshold.
    assert ratelimiter._num_requests == 1
    assert ratelimiter._wait_time == 5.0

    await ratelimiter.handle_async_request(_REQUEST)

    assert ratelimiter._num_requests == 0
    assert ratelimiter._wait_time == 0


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
