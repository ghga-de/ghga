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

"""This file contains general utility api calls"""

from typing import NoReturn

import httpx2
from tenacity import RetryError

from ghga_connector import exceptions


def is_service_healthy(api_url: str, *, timeout_in_seconds: int = 5) -> bool:
    """Check if the corresponding health endpoint is available"""
    # Adjust url so the the health endpoint is actually called
    api_url = api_url.rstrip("/")
    if not api_url.endswith("/health"):
        api_url += "/health"

    return check_url(api_url=api_url, timeout_in_seconds=timeout_in_seconds)


def check_url(api_url: str, *, timeout_in_seconds: int = 5) -> bool:
    """Checks, if an url is reachable within a certain time"""
    try:
        # Don't cache health checks
        response = httpx2.get(url=api_url, timeout=timeout_in_seconds)
    except httpx2.RequestError:
        return False

    status_code = response.status_code
    if status_code != 200:
        return False

    content = response.json()
    return "status" in content and content["status"].lower() == "ok"


def _raise_request_failed(
    request_error: httpx2.RequestError, *, url: str, cause: BaseException
) -> NoReturn:
    """Raise the Connector exception matching a transport-level failure."""
    # Raises the more specific ConnectionFailedError if the connection never stood up
    exceptions.raise_if_connection_failed(request_error=request_error, url=url)
    raise exceptions.RequestFailedError(url=url, reason=str(request_error)) from cause


def handle_request_error(
    exc: RetryError | httpx2.RequestError, *, url: str
) -> httpx2.Response:
    """Translate a request that exhausted its retries into a Connector exception.

    The retry transport re-raises the original exception when the final attempt errored
    and only wraps it in a `RetryError` when the final attempt produced a response (an
    exhausted 5xx, say), so callers have to be prepared for either.

    Returns that final response when there is one, so the caller can inspect its status
    code. Raises otherwise.
    """
    if isinstance(exc, httpx2.RequestError):
        _raise_request_failed(exc, url=url, cause=exc)

    wrapped_exception = exc.last_attempt.exception()
    if isinstance(wrapped_exception, httpx2.RequestError):
        _raise_request_failed(wrapped_exception, url=url, cause=exc)
    if wrapped_exception is not None:
        raise wrapped_exception from exc

    return exc.last_attempt.result()
