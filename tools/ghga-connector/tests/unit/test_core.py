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
#

"""Tests for the core functions of the cli"""

import re

import pytest

from ghga_connector.core.api_calls import is_service_healthy
from tests.fixtures.mock_api.router import mock_health_checks

HEALTHY_API_URL = "https://ghga.de"


@pytest.fixture()
def mock_health_endpoint(monkeypatch):
    """Serve https://ghga.de/health and refuse every other connection.

    Only the one URL is reported as healthy, so this also pins down which URL
    `is_service_healthy` derives from the API URL it is given.
    """
    mock_health_checks(monkeypatch, healthy_url=re.escape(HEALTHY_API_URL))


@pytest.mark.parametrize(
    "api_url,timeout_in_seconds,expected_response",
    [
        ("https://bad_url", 5, False),
        (HEALTHY_API_URL, 5, True),
        (f"{HEALTHY_API_URL}/", 5, True),
        (f"{HEALTHY_API_URL}/health", 5, True),
        (f"{HEALTHY_API_URL}/health/", 5, True),
    ],
)
def test_is_service_healthy(
    api_url: str,
    timeout_in_seconds: int,
    expected_response: bool,
    mock_health_endpoint,
):
    """Test healthy check function"""
    response = is_service_healthy(api_url, timeout_in_seconds=timeout_in_seconds)
    assert response == expected_response
