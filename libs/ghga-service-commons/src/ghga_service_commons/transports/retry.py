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

"""Provides an httpx.AsyncTransport that handles retrying requests on failure."""

import time
from collections.abc import Callable
from contextlib import suppress
from logging import getLogger
from types import TracebackType
from typing import Any

import httpx
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
    """Wait strategy using exponential backoff, not waiting for 429 responses."""
    return wait_exponential_ignore_429(max=config.client_exponential_backoff_max)


def _default_stop_strategy(config: RetryTransportConfig):
    """Basic stop strategy aborting retrying after a configured number of attempts."""
    return stop_after_attempt(config.client_num_retries)


def _log_retry_stats(retry_state: RetryCallState):
    """Basic logger printing high level stats after each retry attempt."""
    if not retry_state.fn:
        log.debug("No wrapped function found in retry state.")
        return

    function_name = retry_state.fn.__qualname__
    attempt_number = retry_state.attempt_number

    # Get internal statistics from the current retry object
    stats = retry_state.retry_object.statistics
    stats["function_name"] = function_name
    stats["time_elapsed"] = round(time.monotonic() - stats["start_time"], 3)
    stats["start_time"] = round(stats["start_time"], 3)
    stats["idle_for"] = round(stats["idle_for"], 3)

    # Enrich with details from current attempt for debugging
    if outcome := retry_state.outcome:
        try:
            result = outcome.result()
        except Exception as exc:
            stats["exception_type"] = type(exc)
            stats["exception_message"] = str(exc)
        else:
            if isinstance(result, httpx.Response):
                stats["response_status_code"] = result.status_code
                stats["response_headers"] = result.headers

    log.info(
        "Retry attempt number %i for function %s.",
        attempt_number,
        function_name,
        extra=stats,
    )


class wait_exponential_ignore_429(wait_exponential):  # noqa: N801
    """Custom exponential backoff strategy not waiting for 429 responses.

    429 responses need to set the `Should-Wait` header to signal to fall back to using
    exponential backoff.
    """

    def __call__(self, retry_state: RetryCallState) -> float:
        """Copied from base class and adjusted."""
        if retry_state.outcome:
            with suppress(Exception):
                result = retry_state.outcome.result()
                if (
                    isinstance(result, httpx.Response)
                    and result.status_code == 429
                    and not result.headers.get("Should-Wait")
                ):
                    return 0
        try:
            exp = self.exp_base ** (retry_state.attempt_number - 1)
            result = self.multiplier * exp
        except OverflowError:
            result = self.max
        return max(max(0, self.min), min(result, self.max))


class AsyncRetryTransport(httpx.AsyncBaseTransport):
    """Custom async Transport adding retry logic on top of AsyncHTTPTransport.

    This adds tenacity based retry logic around HTTP calls.
    Custom wait and stop strategies and logging after each attempt can be injected.
    The default wait strategy uses and exponential backoff, but ignores 429 responses,
    so their retry-after header can be dealt with corrctly, if present.
    """

    def __init__(
        self,
        config: RetryTransportConfig,
        transport: httpx.AsyncBaseTransport,
        wait_strategy: Callable[[RetryTransportConfig], Any] = _default_wait_strategy,
        stop_strategy: Callable[[RetryTransportConfig], Any] = _default_stop_strategy,
        stats_logger: Callable[[RetryCallState], Any] = _log_retry_stats,
    ) -> None:
        self._transport = transport
        self._retry_handler = _configure_retry_handler(
            config,
            wait_strategy=wait_strategy,
            stop_strategy=stop_strategy,
            stats_logger=stats_logger,
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Handles HTTP requests and adds retry logic around calls."""
        return await self._retry_handler(
            fn=self._transport.handle_async_request, request=request
        )

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
):
    """Configure the AsyncRetrying instance that is used for handling retryable responses/exceptions."""
    return AsyncRetrying(
        reraise=config.client_reraise_from_retry_error,
        retry=(
            retry_if_exception_type(
                (
                    httpx.ConnectError,
                    httpx.ConnectTimeout,
                    httpx.TimeoutException,
                )
            )
            | retry_if_result(
                lambda response: response.status_code
                in config.client_retry_status_codes
            )
        ),
        stop=stop_strategy(config),
        wait=wait_strategy(config),
        after=stats_logger,
    )
