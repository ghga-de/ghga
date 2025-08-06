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
#

"""Test the access check adapter."""

from collections.abc import AsyncGenerator
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from ghga_service_commons.utils.utc_dates import utc_datetime
from pytest_httpx import HTTPXMock

from wps.adapters.outbound.http import AccessCheckAdapter, AccessCheckConfig

pytestmark = pytest.mark.asyncio()

DOWNLOAD_ACCESS_URL = "http://test-access:1234"


@pytest_asyncio.fixture(name="access_check", scope="function")
async def fixture_access_check() -> AsyncGenerator[AccessCheckAdapter, None]:
    """Get configured access test adapter."""
    config = AccessCheckConfig(download_access_url=DOWNLOAD_ACCESS_URL)
    async with AccessCheckAdapter.construct(config=config) as adapter:
        yield adapter


async def test_check_download_access(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test checking the download access"""
    check_access = access_check.check_download_access
    valid_until = utc_datetime(2025, 12, 31, 23, 59, 59)
    user_id = uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{user_id}/datasets/some-data-id",
        json=valid_until.isoformat(),
    )
    assert await check_access(user_id, "some-data-id") == valid_until
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{user_id}/datasets/other-data-id",
        text="null",
    )
    assert await check_access(user_id, "other-data-id") is None
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{user_id}/datasets/no-data-id",
        status_code=404,
    )
    assert await check_access(user_id, "no-data-id") is None


async def test_get_download_datasets(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test getting the datasets for download access"""
    get_datasets = access_check.get_accessible_datasets_with_expiration
    valid_until_1 = utc_datetime(2025, 12, 31, 23, 59, 59)
    valid_until_2 = valid_until_1 + timedelta(days=180)
    user_id = uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{user_id}/datasets",
        json={
            "data-id-1": valid_until_1.isoformat(),
            "data-id-2": valid_until_2.isoformat(),
        },
    )
    assert await get_datasets(user_id) == {
        "data-id-1": valid_until_1,
        "data-id-2": valid_until_2,
    }
    no_user_id = uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{no_user_id}/datasets",
        status_code=404,
    )
    assert await get_datasets(no_user_id) == {}
