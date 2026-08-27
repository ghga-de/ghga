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

"""Tests for the mock API harness itself"""

import re
from unittest.mock import patch

import httpx2
import pytest

from ghga_connector.config import get_config
from ghga_connector.core.client import async_client
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.apis import (
    MockApis,
    mock_apis,  # noqa: F401
)
from tests.fixtures.mock_api.router import (
    OffLimitsError,
    is_mocked,
    may_be_reached,
)


@pytest.fixture(scope="function", autouse=True)
def apply_test_config():
    """Apply default test config"""
    with patch("ghga_connector.config.CONFIG", get_test_config()):
        yield


def _destination(url: str, mock_apis: MockApis) -> str:  # noqa: F811
    """Where a request to `url` would be sent."""
    parsed = httpx2.URL(url)
    if is_mocked(parsed, mock_apis.base_urls):
        return "mock"
    return "network" if may_be_reached(parsed) else "refused"


@pytest.mark.parametrize(
    "url, expected",
    [
        # The mocked GHGA APIs, under every spelling of the loopback interface
        ("http://127.0.0.1/upload/boxes", "mock"),
        ("https://127.0.0.1/values", "mock"),
        ("http://localhost/upload/boxes", "mock"),
        # The S3 testcontainer, at whichever address Docker is reached by. Which one it
        # is depends on the environment, so all of them have to be allowed out.
        ("http://localhost:32768/bucket/object", "network"),
        ("http://127.0.0.1:32768/bucket/object", "network"),
        ("http://host.docker.internal:32768/bucket/object", "network"),
        ("http://172.17.0.1:32768/bucket/object", "network"),
        ("http://172.17.0.2:4566/bucket/object", "network"),
        # The internet, including the connector's own live default for the WKVS
        ("https://data.ghga.de/.well-known/values", "refused"),
        ("https://example.org/anything", "refused"),
    ],
)
def test_requests_are_sorted_by_destination(
    url: str,
    expected: str,
    mock_apis: MockApis,  # noqa: F811
):
    """Make sure mock, testcontainer and internet traffic are told apart correctly."""
    assert _destination(url, mock_apis) == expected


@pytest.mark.asyncio
async def test_requests_to_the_internet_are_refused(
    mock_apis: MockApis,  # noqa: F811
):
    """Make sure a call the mocks don't cover cannot leave the test suite.

    The connector ships a live GHGA URL as its `wkvs_api_url` default, so a test that
    failed to apply the test config would otherwise call production for real.
    """
    # `Config` is a factory, so reach the model class through an instance
    live_default = type(get_test_config()).model_fields["wkvs_api_url"].default
    assert live_default.startswith("https://"), "expected a real URL as the default"
    assert "127.0.0.1" not in live_default

    async with async_client(purpose="download") as client:
        with pytest.raises(OffLimitsError, match=re.escape(live_default)):
            await client.get(f"{live_default}/values")


@pytest.mark.asyncio
@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
async def test_mocked_apis_are_reachable_under_either_loopback_name(
    mock_apis: MockApis,  # noqa: F811
    host: str,
):
    """Make sure refusing the internet doesn't also refuse the mocks."""
    wkvs_url = httpx2.URL(get_config().wkvs_api_url).copy_with(host=host)

    async with async_client(purpose="download") as client:
        response = await client.get(f"{wkvs_url}/values")

    assert response.status_code == 200
    assert response.json()["dcs_api_url"]
    assert mock_apis.wkvs.requests
