# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

import pytest
from pytest_httpx import HTTPXMock, httpx_mock  # noqa: F401

from ghga_connector.core.api_calls import is_service_healthy


@pytest.mark.httpx_mock(
    assert_all_responses_were_requested=False,
    assert_all_requests_were_expected=False,
)
@pytest.mark.parametrize(
    "api_url,timeout_in_seconds,expected_response",
    [
        ("https://bad_url", 5, False),
        ("https://ghga.de", 5, True),
        ("https://ghga.de/", 5, True),
        ("https://ghga.de/health", 5, True),
        ("https://ghga.de/health/", 5, True),
    ],
)
def test_is_service_healthy(
    api_url: str,
    timeout_in_seconds: int,
    expected_response: bool,
    httpx_mock: HTTPXMock,  # noqa: F811
):
    """Test healthy check function"""
    httpx_mock.add_response(
        url="https://ghga.de/health", status_code=200, json={"status": "OK"}
    )
    response = is_service_healthy(api_url, timeout_in_seconds=timeout_in_seconds)
    assert response == expected_response
