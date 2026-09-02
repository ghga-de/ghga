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

"""Tests for the retry transport: retry behavior, wait strategy, logging and cleanup."""

import logging
from collections.abc import Callable
from unittest.mock import AsyncMock

import httpx2
import pytest
from tenacity import AsyncRetrying, RetryCallState, RetryError

from ghga_service_commons.transports.config import RetryTransportConfig
from ghga_service_commons.transports.retry import (
    AsyncRetryTransport,
    _default_wait_strategy,
    _log_before_attempt,
    _log_retry_stats,
)


def _wait_strategy(max_backoff: int = 60):
    """Build the wait strategy the retry transport actually uses."""
    return _default_wait_strategy(
        RetryTransportConfig(client_exponential_backoff_max=max_backoff)
    )


LOGGER_NAME = "ghga_service_commons.transports.retry"
RETRYABLE_STATUS_CODE = 503
_REQUEST = httpx2.Request("GET", "http://test")


class _TrackedResponse(httpx2.Response):
    """Response that records whether it was closed, to detect leaked connections."""

    def __init__(self, status_code: int) -> None:
        super().__init__(status_code=status_code)
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True
        await super().aclose()


class _FailingCloseResponse(httpx2.Response):
    """Response whose aclose() always raises; counts calls to catch a double close."""

    def __init__(self, status_code: int) -> None:
        super().__init__(status_code=status_code)
        self.close_calls = 0

    async def aclose(self) -> None:
        self.close_calls += 1
        raise RuntimeError("aclose failed")


def _no_wait(config: RetryTransportConfig) -> Callable[[RetryCallState], float]:
    """Wait strategy injecting zero delay so retry behavior tests stay fast."""
    return lambda retry_state: 0


def _mock_transport(side_effect: list[object]) -> AsyncMock:
    """Build a transport mock whose calls yield the given responses/exceptions in turn."""
    transport = AsyncMock(spec=httpx2.AsyncBaseTransport)
    transport.handle_async_request = AsyncMock(side_effect=side_effect)
    return transport


def _retry_transport(
    transport: AsyncMock, *, num_retries: int = 3, reraise: bool = True
) -> AsyncRetryTransport:
    """Wrap the transport in a retry transport that does not actually wait between tries."""
    return AsyncRetryTransport(
        config=RetryTransportConfig(
            client_num_retries=num_retries,
            client_reraise_from_retry_error=reraise,
        ),
        transport=transport,
        wait_strategy=_no_wait,
    )


def _retry_state(
    *,
    result: httpx2.Response | None = None,
    exception: BaseException | None = None,
    attempt_number: int = 1,
    fn: Callable[..., object] | None = None,
) -> RetryCallState:
    """Construct a RetryCallState carrying the given outcome for strategy/logger tests."""
    state = RetryCallState(AsyncRetrying(), fn=fn, args=(), kwargs={})
    state.attempt_number = attempt_number
    if exception is not None:
        state.set_exception((type(exception), exception, exception.__traceback__))
    elif result is not None:
        state.set_result(result)
    return state


def _named_function() -> None:
    """Stand-in wrapped function so loggers have a qualified name to report."""


@pytest.mark.asyncio
async def test_returns_first_successful_response():
    """Ensure a non-retryable success is returned immediately without a second attempt."""
    response = _TrackedResponse(httpx2.codes.OK)
    transport = _mock_transport([response])

    result = await _retry_transport(transport).handle_async_request(_REQUEST)

    assert result is response
    assert transport.handle_async_request.await_count == 1
    assert not response.closed


@pytest.mark.asyncio
async def test_retries_retryable_status_until_success():
    """Ensure retryable status codes are retried until a successful response is received."""
    responses = [
        _TrackedResponse(RETRYABLE_STATUS_CODE),
        _TrackedResponse(RETRYABLE_STATUS_CODE),
        _TrackedResponse(httpx2.codes.OK),
    ]
    transport = _mock_transport(responses)  # type: ignore[arg-type]

    result = await _retry_transport(transport).handle_async_request(_REQUEST)

    assert result is responses[-1]
    assert transport.handle_async_request.await_count == 3


@pytest.mark.asyncio
async def test_does_not_retry_non_retryable_status():
    """Ensure a non-retryable status code is returned as-is after a single attempt."""
    response = _TrackedResponse(httpx2.codes.NOT_FOUND)
    transport = _mock_transport([response])

    result = await _retry_transport(transport).handle_async_request(_REQUEST)

    assert result is response
    assert transport.handle_async_request.await_count == 1
    assert not response.closed


@pytest.mark.parametrize(
    "exception",
    [
        httpx2.ConnectTimeout("timeout"),
        httpx2.ConnectError("network"),
        httpx2.RemoteProtocolError("protocol"),
        httpx2.ProxyError("proxy"),
    ],
)
@pytest.mark.asyncio
async def test_retries_on_retryable_exception(exception: Exception):
    """Ensure configured retryable exception types trigger a retry that can then succeed."""
    response = _TrackedResponse(httpx2.codes.OK)
    transport = _mock_transport([exception, response])

    result = await _retry_transport(transport).handle_async_request(_REQUEST)

    assert result is response
    assert transport.handle_async_request.await_count == 2


@pytest.mark.asyncio
async def test_does_not_retry_unlisted_exception():
    """Ensure an exception type outside the retryable set propagates without any retry."""
    transport = _mock_transport([RuntimeError("boom")])

    with pytest.raises(RuntimeError):
        await _retry_transport(transport).handle_async_request(_REQUEST)

    assert transport.handle_async_request.await_count == 1


@pytest.mark.asyncio
async def test_reraises_original_exception_when_configured():
    """Ensure with reraise enabled the original exception surfaces after retries are exhausted."""
    transport = _mock_transport([httpx2.ConnectError("c")] * 3)

    with pytest.raises(httpx2.ConnectError):
        await _retry_transport(
            transport, num_retries=3, reraise=True
        ).handle_async_request(_REQUEST)

    assert transport.handle_async_request.await_count == 3


@pytest.mark.asyncio
async def test_raises_retry_error_when_not_reraising():
    """Ensure with reraise disabled the exhausted exception is wrapped in a RetryError."""
    exception = httpx2.ConnectError("c")
    transport = _mock_transport([exception] * 3)

    with pytest.raises(RetryError) as exc_info:
        await _retry_transport(
            transport, num_retries=3, reraise=False
        ).handle_async_request(_REQUEST)

    assert exc_info.value.last_attempt is not None
    assert exc_info.value.last_attempt.exception() is exception
    assert transport.handle_async_request.await_count == 3


@pytest.mark.asyncio
async def test_retried_responses_are_closed():
    """Retried responses are closed, the returned one is not.

    Each holds a pool connection until read or closed, so leaving them open leaks.
    """
    responses = [
        _TrackedResponse(RETRYABLE_STATUS_CODE),
        _TrackedResponse(RETRYABLE_STATUS_CODE),
        _TrackedResponse(httpx2.codes.OK),
    ]
    transport = _mock_transport(responses)  # type: ignore[arg-type]

    result = await _retry_transport(transport).handle_async_request(_REQUEST)

    *retried, returned = responses
    assert result is returned
    assert all(response.closed for response in retried)
    assert not returned.closed


@pytest.mark.asyncio
async def test_exhausted_retries_close_last_response():
    """Ensure when retries are exhausted, the final unreturned response is closed."""
    responses = [_TrackedResponse(RETRYABLE_STATUS_CODE) for _ in range(3)]
    transport = _mock_transport(responses)  # type: ignore[arg-type]

    with pytest.raises(RetryError):
        await _retry_transport(transport).handle_async_request(_REQUEST)

    assert all(response.closed for response in responses)


@pytest.mark.asyncio
async def test_cleanup_close_error_does_not_mask_original_exception():
    """Ensure a failing aclose() during cleanup does not replace the underlying exception."""
    responses = [
        _TrackedResponse(RETRYABLE_STATUS_CODE),
        _TrackedResponse(RETRYABLE_STATUS_CODE),
        _FailingCloseResponse(RETRYABLE_STATUS_CODE),
    ]
    transport = _mock_transport(responses)  # type: ignore[arg-type]

    with pytest.raises(RetryError):
        await _retry_transport(transport).handle_async_request(_REQUEST)


@pytest.mark.asyncio
async def test_pre_attempt_close_error_clears_latest_response():
    """Ensure a failing pre-attempt aclose() clears the reference so it is not closed twice."""
    failing = _FailingCloseResponse(RETRYABLE_STATUS_CODE)
    transport = _mock_transport([failing])

    with pytest.raises(RuntimeError):
        await _retry_transport(transport).handle_async_request(_REQUEST)

    assert failing.close_calls == 1


@pytest.mark.asyncio
async def test_aclose_delegates_to_wrapped_transport():
    """Ensure closing the retry transport closes the transport it wraps."""
    transport = _mock_transport([])

    await _retry_transport(transport).aclose()

    transport.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_context_manager_closes_transport():
    """Ensure exiting the async context manager closes the wrapped transport."""
    transport = _mock_transport([])

    async with _retry_transport(transport) as retry_transport:
        assert isinstance(retry_transport, AsyncRetryTransport)

    transport.aclose.assert_awaited_once()


def test_wait_strategy_treats_429_like_any_other_retryable_status():
    """A 429 gets the ordinary backoff; the layer below holds the Retry-After."""
    wait = _wait_strategy()
    state = _retry_state(result=httpx2.Response(429), attempt_number=3)

    assert wait(state) == 4


def test_wait_strategy_backs_off_for_other_status():
    """Ensure non-429 responses use the regular exponential backoff."""
    wait = _wait_strategy()
    state = _retry_state(result=httpx2.Response(503), attempt_number=3)

    assert wait(state) == 4


def test_wait_strategy_caps_at_max():
    """Ensure the computed backoff never exceeds the configured maximum."""
    wait = _wait_strategy(5)
    state = _retry_state(result=httpx2.Response(503), attempt_number=10)

    assert wait(state) == 5


def test_wait_strategy_handles_failed_outcome():
    """Ensure a failed outcome is backed off without inspecting a result."""
    wait = _wait_strategy()
    state = _retry_state(exception=httpx2.ConnectError("boom"), attempt_number=1)

    assert wait(state) == 1


def test_log_before_attempt_records_attempt(caplog: pytest.LogCaptureFixture):
    """Ensure the before-attempt logger emits the function name and attempt number."""
    state = _retry_state(fn=_named_function, attempt_number=2)

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        _log_before_attempt(state)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.attempt_number == 2  # type: ignore[attr-defined]
    assert record.function_name == _named_function.__qualname__  # type: ignore[attr-defined]


def test_log_retry_stats_includes_response_status(caplog: pytest.LogCaptureFixture):
    """Ensure that for a response outcome the stats logger records the status code."""
    state = _retry_state(fn=_named_function, result=httpx2.Response(503))

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        _log_retry_stats(state)

    assert caplog.records[0].response_status_code == 503  # type: ignore[attr-defined]


def test_log_retry_stats_includes_exception_details(caplog: pytest.LogCaptureFixture):
    """Ensure that for a failed outcome the stats logger records the exception type and message."""
    state = _retry_state(fn=_named_function, exception=httpx2.ConnectError("boom"))

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        _log_retry_stats(state)

    record = caplog.records[0]
    assert record.exception_type is httpx2.ConnectError  # type: ignore[attr-defined]
    assert "boom" in record.exception_message  # type: ignore[attr-defined]
