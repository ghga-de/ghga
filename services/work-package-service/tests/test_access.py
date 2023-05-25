# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from typing import AsyncGenerator

from pytest import mark
from pytest_asyncio import fixture as async_fixture
from pytest_httpx import HTTPXMock

from wps.adapters.outbound.http import AccessCheckAdapter, AccessCheckConfig

DOWNLOAD_ACCESS_URL = "http://test-access:1234"


@async_fixture(name="access_check")
async def fixture_access_check() -> AsyncGenerator[AccessCheckAdapter, None]:
    """Get configured access test adapter."""
    config = AccessCheckConfig(download_access_url=DOWNLOAD_ACCESS_URL)
    async with AccessCheckAdapter.construct(config=config) as adapter:
        yield adapter


@mark.asyncio
async def test_check_download_access(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test checking the download access"""
    check_access = access_check.check_download_access
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/some-user-id/datasets/some-data-id",
        text="true",
    )
    assert await check_access("some-user-id", "some-data-id") is True
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/some-user-id/datasets/other-data-id",
        text="false",
    )
    assert await check_access("some-user-id", "other-data-id") is False
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/some-user-id/datasets/no-data-id",
        status_code=404,
    )
    assert await check_access("some-user-id", "no-data-id") is False


@mark.asyncio
async def test_get_download_datasets(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test getting the datasets for download access"""
    get_datasets = access_check.get_datasets_with_download_access
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/some-user-id/datasets",
        json=["some-data-id", "another-data-id"],
    )
    assert await get_datasets("some-user-id") == ["some-data-id", "another-data-id"]
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/no-user-id/datasets",
        status_code=404,
    )
    assert await get_datasets("no-user-id") == []
