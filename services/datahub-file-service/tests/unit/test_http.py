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

"""Unit tests for the HTTP client helpers"""

import httpx2
import pytest

from dhfs.adapters.outbound.http import (
    ConnectionFailedError,
    raise_if_connection_failed,
)


@pytest.mark.parametrize(
    "request_error, expected_reason",
    [
        (
            httpx2.ConnectError("All connection attempts failed"),
            "All connection attempts failed",
        ),
        (httpx2.ConnectTimeout(""), "httpx2.ConnectTimeout"),
    ],
)
def test_connection_failed_reason_is_never_blank(
    request_error: httpx2.RequestError, expected_reason: str
):
    """Ensure a connection failure names its cause even when httpx gives no message."""
    url = "https://example.org/api"
    with pytest.raises(ConnectionFailedError) as exc_info:
        raise_if_connection_failed(request_error=request_error, url=url)

    assert expected_reason in str(exc_info.value)
