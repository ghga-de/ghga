# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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
#

"""Tests for the core functions of the cli"""
from typing import Optional

import pytest

from ghga_connector.core.exceptions import (
    CollectiveError,
    FatalError,
    MaxRetriesReachedError,
    RetryAbortError,
)
from ghga_connector.core.main import check_url
from ghga_connector.core.retry import WithRetry


@pytest.mark.parametrize(
    "api_url,wait_time,expected_response",
    # Google has a higher availability than ghga.de
    [("https://www.google.de/", 1000, True), ("https://bad_url", 1000, False)],
)
def test_check_url(api_url: str, wait_time: int, expected_response: bool):
    """
    Test the check_url function
    """
    response = check_url(api_url, wait_time=wait_time)
    assert response == expected_response


@pytest.mark.parametrize(
    "retry_exceptions,final_exception",
    [
        ([None], None),
        ([RuntimeError], RuntimeError),
        (
            [RuntimeError, TypeError, None],
            None,
        ),
        (
            [RuntimeError, TypeError, ValueError],
            MaxRetriesReachedError,
        ),
        (
            [RuntimeError, TypeError, FatalError],
            RetryAbortError,
        ),
    ],
)
def test_retry(
    retry_exceptions: list[type[Optional[Exception]]],
    final_exception: type[Optional[Exception]],
):
    """
    Test the Retry class decorator
    """
    # initialize state for the decorator
    WithRetry.set_retries(len(retry_exceptions) - 1)

    curr_retry = 0

    @WithRetry
    def exception_producer():
        """
        Generate exceptions based on expected behavior
        Distinguish between fatal and non fatal exceptions
        """
        nonlocal curr_retry
        exception = retry_exceptions[curr_retry]
        curr_retry += 1

        if isinstance(exception, Exception):
            raise exception

    try:
        exception_producer()
    except Exception as final_error:
        assert isinstance(final_error, final_exception)
        if isinstance(final_error, CollectiveError):
            for idx, retry_error in enumerate(final_error.causes):
                assert isinstance(retry_error, retry_exceptions[idx])
    finally:
        WithRetry._max_retries = None
