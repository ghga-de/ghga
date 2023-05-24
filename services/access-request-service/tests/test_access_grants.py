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

"""Test the access grant adapter."""

import json
from typing import AsyncGenerator

import httpx
from ghga_service_commons.utils.utc_dates import DateTimeUTC
from pytest import mark, raises
from pytest_asyncio import fixture as async_fixture
from pytest_httpx import HTTPXMock

from ars.adapters.outbound.http import AccessGrantsAdapter, AccessGrantsConfig

datetime_utc = DateTimeUTC.construct

DOWNLOAD_ACCESS_URL = "http://test-access:1234"

USER_ID = "some-user-id"
DATASET_ID = "some-dataset-id"
VALID_FROM = datetime_utc(2020, 1, 1, 0, 0)
VALID_UNTIL = datetime_utc(2020, 12, 31, 23, 59)

URL = f"{DOWNLOAD_ACCESS_URL}/users/{USER_ID}/datasets/{DATASET_ID}"


@async_fixture(name="access_grant")
async def fixture_access_grant() -> AsyncGenerator[AccessGrantsAdapter, None]:
    """Get configured access grant test adapter."""
    config = AccessGrantsConfig(download_access_url=DOWNLOAD_ACCESS_URL)
    async with AccessGrantsAdapter.construct(config=config) as adapter:
        yield adapter


@mark.asyncio
async def test_grant_download_access(
    access_grant: AccessGrantsAdapter, httpx_mock: HTTPXMock
):
    """Test granting download access"""
    grant_access = access_grant.grant_download_access
    httpx_mock.add_response(method="POST", url=URL, status_code=204)

    await grant_access(
        user_id=USER_ID,
        dataset_id=DATASET_ID,
        valid_from=VALID_FROM,
        valid_until=VALID_UNTIL,
    )

    request = httpx_mock.get_request()
    assert request
    assert json.loads(request.content) == {
        "valid_from": VALID_FROM.isoformat(),
        "valid_until": VALID_UNTIL.isoformat(),
    }


@mark.asyncio
async def test_grant_download_access_with_invalid_dates(
    access_grant: AccessGrantsAdapter,
):
    """Test granting download access for invalid dates"""
    grant_access = access_grant.grant_download_access

    with raises(
        access_grant.AccessGrantsInvalidPeriodError, match="Invalid validity period"
    ):
        await grant_access(
            user_id=USER_ID,
            dataset_id=DATASET_ID,
            valid_from=VALID_UNTIL,
            valid_until=VALID_FROM,
        )


@mark.asyncio
async def test_grant_download_access_with_server_error(
    access_grant: AccessGrantsAdapter, httpx_mock: HTTPXMock
):
    """Test granting download access when there is a server error"""
    grant_access = access_grant.grant_download_access
    httpx_mock.add_response(method="POST", url=URL, status_code=500)

    with raises(
        access_grant.AccessGrantsError, match="Unexpected HTTP response status code 500"
    ):
        await grant_access(
            user_id=USER_ID,
            dataset_id=DATASET_ID,
            valid_from=VALID_FROM,
            valid_until=VALID_UNTIL,
        )


@mark.asyncio
async def test_grant_download_access_with_timeout(
    access_grant: AccessGrantsAdapter, httpx_mock: HTTPXMock
):
    """Test granting download access when there is a network timeout"""
    grant_access = access_grant.grant_download_access
    httpx_mock.add_exception(httpx.ReadTimeout("Simulated network problem"))

    with raises(access_grant.AccessGrantsError, match="Simulated network problem"):
        await grant_access(
            user_id=USER_ID,
            dataset_id=DATASET_ID,
            valid_from=VALID_FROM,
            valid_until=VALID_UNTIL,
        )
