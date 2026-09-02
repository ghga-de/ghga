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

"""Provides an httpx2.AsyncTransport that handles retrying requests on failure."""

import time
from collections.abc import Callable
from logging import getLogger
from types import TracebackType
from typing import Any

import httpx2
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)

from ghga_service_commons.transports.config import RetryTransportConfig

log = getLogger(__name__)


def _default_wait_strategy(config: RetryTransportConfig):
    """Exponential backoff.

    A 429 needs no special case: the rate limiting layer holds the server's Retry-After
    as a deadline the next attempt blocks on, so the longer of the two waits decides.
    """
    return wait_exponential(max=config.client_exponential_backoff_max)


def _default_stop_strategy(config: RetryTransportConfig):
    """Stop after the configured number of attempts."""
    return stop_after_attempt(config.client_num_retries)


def _log_retry_stats(retry_state: RetryCallState):
    """Log stats after each retry attempt."""
    if not retry_state.fn:
        log.debug("No wrapped function found in retry state.")
        return

    function_name = retry_state.fn.__qualname__
    attempt_number = retry_state.attempt_number

    # Build from retry_state; the retry object's own stats dict is shared across requests.
    stats: dict[str, Any] = {
        "function_name": function_name,
        "attempt_number": attempt_number,
        "start_time": round(retry_state.start_time, 3),
        "idle_for": round(retry_state.idle_for, 3),
        "time_elapsed": round(time.monotonic() - retry_state.start_time, 3),
    }

    if (outcome := retry_state.outcome) is not None:
        if outcome.failed:
            exc = outcome.exception()
            stats["exception_type"] = type(exc)
            stats["exception_message"] = str(exc)
        elif isinstance(result := outcome.result(), httpx2.Response):
            stats["response_status_code"] = result.status_code
            stats["response_headers"] = result.headers

    log.info(
        "Retry attempt number %i for function %s.",
        attempt_number,
        function_name,
        extra=stats,
    )


def _log_before_attempt(retry_state: RetryCallState):
    """Log the function and attempt number before each attempt."""
    if not retry_state.fn:
        log.debug("No wrapped function found in retry state.")
        return

    function_name = retry_state.fn.__qualname__
    attempt_number = retry_state.attempt_number

    log.info(
        "Starting attempt number %i for function %s.",
        attempt_number,
        function_name,
        extra={
            "function_name": function_name,
            "attempt_number": attempt_number,
        },
    )


class AsyncRetryTransport(httpx2.AsyncBaseTransport):
    """Retries failed requests using tenacity.

    The wait and stop strategies and the per-attempt logging can be injected. The
    default waits with exponential backoff.
    """

    def __init__(  # noqa: PLR0913
        self,
        config: RetryTransportConfig,
        transport: httpx2.AsyncBaseTransport,
        wait_strategy: Callable[[RetryTransportConfig], Any] = _default_wait_strategy,
        stop_strategy: Callable[[RetryTransportConfig], Any] = _default_stop_strategy,
        stats_logger: Callable[[RetryCallState], Any] = _log_retry_stats,
        before_logger: Callable[[RetryCallState], Any] = _log_before_attempt,
    ) -> None:
        self._transport = transport
        self._retry_handler = _configure_retry_handler(
            config,
            wait_strategy=wait_strategy,
            stop_strategy=stop_strategy,
            stats_logger=stats_logger,
            before_logger=before_logger,
        )

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Send the request, retrying on failure."""
        # Close each attempt's response before the next one, leaving only the last open.
        latest_response: httpx2.Response | None = None

        async def _attempt() -> httpx2.Response:
            nonlocal latest_response
            if latest_response is not None:
                # Clear it so the cleanup below cannot close the same response twice.
                try:
                    await latest_response.aclose()
                finally:
                    latest_response = None
            # Pass positionally: Otel's httpx instrumentation reads args[0].
            latest_response = await self._transport.handle_async_request(request)
            return latest_response

        try:
            return await self._retry_handler(_attempt)
        except BaseException:
            # Also covers the RetryError raised once all attempts are exhausted.
            if latest_response is not None:
                try:
                    await latest_response.aclose()
                except Exception:
                    log.warning(
                        "Failed to close response during cleanup.", exc_info=True
                    )
            raise

    async def aclose(self) -> None:  # noqa: D102
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncRetryTransport":  # noqa: D105
        return self

    async def __aexit__(  # noqa: D105
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self.aclose()


def _configure_retry_handler(
    config: RetryTransportConfig,
    wait_strategy: Callable[[RetryTransportConfig], Any],
    stop_strategy: Callable[[RetryTransportConfig], Any],
    stats_logger: Callable[[RetryCallState], Any],
    before_logger: Callable[[RetryCallState], Any],
):
    """Build the tenacity AsyncRetrying instance."""
    return AsyncRetrying(
        reraise=config.client_reraise_from_retry_error,
        retry=(
            retry_if_exception_type(
                (
                    httpx2.TimeoutException,
                    httpx2.NetworkError,
                    httpx2.RemoteProtocolError,
                    httpx2.ProxyError,
                )
            )
            | retry_if_result(
                lambda response: (
                    response.status_code in config.client_retry_status_codes
                )
            )
        ),
        stop=stop_strategy(config),
        wait=wait_strategy(config),
        before=before_logger,
        after=stats_logger,
    )
