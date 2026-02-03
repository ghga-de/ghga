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
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from ghga_service_commons.utils.utc_dates import utc_datetime
from pytest_httpx import HTTPXMock

from wps.adapters.outbound.http import AccessCheckAdapter, AccessCheckConfig

pytestmark = pytest.mark.asyncio()

BASE_ACCESS_URL = "http://test-access:1234"
DOWNLOAD_ACCESS_URL = f"{BASE_ACCESS_URL}/download-access"
UPLOAD_ACCESS_URL = f"{BASE_ACCESS_URL}/upload-access"
TEST_USER_ID = UUID("69f1a954-7387-4b70-8bc4-9bf98810d442")
BOX_ID1 = UUID("62659dd1-51b6-4a87-8614-ca20c873ce38")
BOX_ID2 = UUID("f4ed5888-765e-4f0c-a012-2c8d27dd6ed8")
VALID_UNTIL1 = utc_datetime(2025, 12, 31, 23, 59, 59)
VALID_UNTIL2 = VALID_UNTIL1 + timedelta(days=180)


@pytest_asyncio.fixture(name="access_check", scope="function")
async def fixture_access_check() -> AsyncGenerator[AccessCheckAdapter]:
    """Get configured access test adapter."""
    config = AccessCheckConfig(access_url=BASE_ACCESS_URL)  # type: ignore
    async with AccessCheckAdapter.construct(config=config) as adapter:
        yield adapter


async def test_check_download_access(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test checking the download access"""
    check_access = access_check.check_download_access

    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{TEST_USER_ID}/datasets/some-data-id",
        json=VALID_UNTIL1.isoformat(),
    )
    assert await check_access(TEST_USER_ID, "some-data-id") == VALID_UNTIL1
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{TEST_USER_ID}/datasets/other-data-id",
        text="null",
    )
    assert await check_access(TEST_USER_ID, "other-data-id") is None
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{TEST_USER_ID}/datasets/no-data-id",
        status_code=404,
    )
    assert await check_access(TEST_USER_ID, "no-data-id") is None

    # Test other error status codes
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{TEST_USER_ID}/datasets/some-data-id",
        status_code=500,
    )
    with pytest.raises(
        AccessCheckAdapter.AccessCheckError,
        match="Unexpected response when checking download access for a dataset:"
        " 500 Internal Server Error",
    ):
        await check_access(TEST_USER_ID, "some-data-id")

    # Test invalid datetime as retrieved value
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{TEST_USER_ID}/datasets/some-data-id",
        json="Not a valid date",
    )
    with pytest.raises(
        AccessCheckAdapter.AccessCheckError,
        match="Invalid date in response when checking download access for a dataset",
    ):
        await check_access(TEST_USER_ID, "some-data-id")


async def test_get_download_datasets(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test getting the datasets for download access"""
    get_datasets = access_check.get_accessible_datasets_with_expiration

    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{TEST_USER_ID}/datasets",
        json={
            "data-id-1": VALID_UNTIL1.isoformat(),
            "data-id-2": VALID_UNTIL2.isoformat(),
        },
    )
    assert await get_datasets(TEST_USER_ID) == {
        "data-id-1": VALID_UNTIL1,
        "data-id-2": VALID_UNTIL2,
    }
    no_user_id = uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{no_user_id}/datasets",
        status_code=404,
    )
    assert await get_datasets(no_user_id) == {}

    # Test for other status translation
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{no_user_id}/datasets",
        status_code=500,
    )
    with pytest.raises(
        AccessCheckAdapter.AccessCheckError,
        match="Unexpected response when fetching download access list:"
        " 500 Internal Server Error",
    ):
        await get_datasets(no_user_id)


async def test_get_accessible_boxes_with_expiration(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test retrieving a list of boxes to which the user has access"""
    get_boxes = access_check.get_accessible_boxes_with_expiration

    # Test successful response with multiple boxes
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{TEST_USER_ID}/boxes",
        json={
            str(BOX_ID1): VALID_UNTIL1.isoformat(),
            str(BOX_ID2): VALID_UNTIL2.isoformat(),
        },
    )
    result = await get_boxes(TEST_USER_ID)
    expected = {
        BOX_ID1: VALID_UNTIL1,
        BOX_ID2: VALID_UNTIL2,
    }
    assert result == expected

    # Test user with no accessible boxes (404 response)
    no_user_id = uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{no_user_id}/boxes",
        status_code=404,
    )
    assert await get_boxes(no_user_id) == {}

    # Test for other status translation
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{no_user_id}/boxes",
        status_code=500,
    )
    with pytest.raises(
        AccessCheckAdapter.AccessCheckError,
        match="Unexpected response when fetching upload access list:"
        " 500 Internal Server Error",
    ):
        await get_boxes(no_user_id)


async def test_get_accessible_boxes_invalid_response_id(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test the `get_accessible_boxes_with_expiration` method when the Access API
    returns an invalid box ID.
    """
    get_boxes = access_check.get_accessible_boxes_with_expiration
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{TEST_USER_ID}/boxes",
        json={
            str(BOX_ID1): VALID_UNTIL1.isoformat(),
            "invalid-id": VALID_UNTIL2.isoformat(),
        },
    )
    with pytest.raises(
        AccessCheckAdapter.AccessCheckError,
        match="Invalid UUID when fetching upload access list",
    ):
        await get_boxes(TEST_USER_ID)


async def test_get_accessible_boxes_invalid_response_datetime(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test the `get_accessible_boxes_with_expiration` method when the Access API
    returns an invalid datetime.
    """
    get_boxes = access_check.get_accessible_boxes_with_expiration
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{TEST_USER_ID}/boxes",
        json={
            str(BOX_ID1): VALID_UNTIL1.isoformat(),
            str(BOX_ID2): "Invalid Datetime",
        },
    )
    with pytest.raises(AccessCheckAdapter.AccessCheckError):
        await get_boxes(TEST_USER_ID)


async def test_check_upload_access(
    access_check: AccessCheckAdapter, httpx_mock: HTTPXMock
):
    """Test checking the upload access"""
    check_access = access_check.check_upload_access

    # Test successful access check
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{TEST_USER_ID}/boxes/{BOX_ID1}",
        json=VALID_UNTIL1.isoformat(),
    )
    assert await check_access(TEST_USER_ID, BOX_ID1) == VALID_UNTIL1

    # Test null response (no access)
    other_box_id = uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{TEST_USER_ID}/boxes/{other_box_id}",
        text="null",
    )
    assert await check_access(TEST_USER_ID, other_box_id) is None

    # Test 404 response (box not found)
    no_box_id = uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{TEST_USER_ID}/boxes/{no_box_id}",
        status_code=404,
    )
    assert await check_access(TEST_USER_ID, no_box_id) is None

    # Test other error status codes
    error_box_id = uuid4()
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{TEST_USER_ID}/boxes/{error_box_id}",
        status_code=500,
    )
    with pytest.raises(
        AccessCheckAdapter.AccessCheckError,
        match="Unexpected response when checking upload access to a box:"
        " 500 Internal Server Error",
    ):
        await check_access(TEST_USER_ID, error_box_id)

    # Test invalid datetime as retrieved value
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{TEST_USER_ID}/boxes/{BOX_ID2}",
        json="Not a valid date",
    )
    with pytest.raises(
        AccessCheckAdapter.AccessCheckError,
        match="Invalid date in response when checking upload access to a box",
    ):
        await check_access(TEST_USER_ID, BOX_ID2)
