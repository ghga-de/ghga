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

"""Unit tests for the access client"""

from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from hexkit.utils import now_utc_ms_prec
from pytest_httpx import HTTPXMock

from tests.fixtures import ConfigFixture
from uos.adapters.outbound.http import AccessClient

pytestmark = pytest.mark.asyncio()

TEST_USER_ID = UUID("f698158d-8417-4368-bb45-349277bc45ee")
TEST_IVA_ID = UUID("8f9b2d54-bccc-42e9-8df4-7df5c5c610d2")
TEST_BOX_ID = UUID("05bbc2ea-d718-4d05-b7b0-1e14b19b90d8")
VALID_FROM = now_utc_ms_prec() - timedelta(minutes=5)
VALID_UNTIL = VALID_FROM + timedelta(minutes=5)


async def test_grant_upload_access(config: ConfigFixture, httpx_mock: HTTPXMock):
    """Test the grant_upload_access function"""
    access_client = AccessClient(config=config.config)

    # Happy path
    httpx_mock.add_response(200)
    await access_client.grant_upload_access(
        user_id=TEST_USER_ID,
        iva_id=TEST_IVA_ID,
        box_id=TEST_BOX_ID,
        valid_from=VALID_FROM,
        valid_until=VALID_UNTIL,
    )  # no error == success

    # Check off-normal status code
    httpx_mock.add_response(500, json={"error": "Some error occurred."})
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.grant_upload_access(
            user_id=TEST_USER_ID,
            iva_id=TEST_IVA_ID,
            box_id=TEST_BOX_ID,
            valid_from=VALID_FROM,
            valid_until=VALID_UNTIL,
        )

    # Check 403 status code
    httpx_mock.add_response(403, json={"error": "Forbidden"})
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.grant_upload_access(
            user_id=TEST_USER_ID,
            iva_id=TEST_IVA_ID,
            box_id=TEST_BOX_ID,
            valid_from=VALID_FROM,
            valid_until=VALID_UNTIL,
        )

    # Check 404 status code
    httpx_mock.add_response(404, json={"error": "Not found"})
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.grant_upload_access(
            user_id=TEST_USER_ID,
            iva_id=TEST_IVA_ID,
            box_id=TEST_BOX_ID,
            valid_from=VALID_FROM,
            valid_until=VALID_UNTIL,
        )


async def test_get_accessible_upload_boxes(
    config: ConfigFixture, httpx_mock: HTTPXMock
):
    """Test the get_accessible_upload_boxes function"""
    access_client = AccessClient(config=config.config)

    # Happy path with multiple boxes
    some_datetime = now_utc_ms_prec().isoformat()
    box_to_expiration: dict[UUID, str] = {uuid4(): some_datetime for _ in range(3)}
    httpx_mock.add_response(200, json=[str(box_id) for box_id in box_to_expiration])
    result = await access_client.get_accessible_upload_boxes(user_id=TEST_USER_ID)
    assert result == list(box_to_expiration.keys())

    # Happy path with empty list
    httpx_mock.add_response(200, json=[])
    result = await access_client.get_accessible_upload_boxes(user_id=TEST_USER_ID)
    assert result == []

    # Check off-normal status code
    httpx_mock.add_response(500, json={"error": "Some error occurred."})
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.get_accessible_upload_boxes(user_id=TEST_USER_ID)

    # Check 403 status code
    httpx_mock.add_response(403, json={"error": "Forbidden"})
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.get_accessible_upload_boxes(user_id=TEST_USER_ID)

    # Check 404 status code
    httpx_mock.add_response(404, json={"error": "Not found"})
    result = await access_client.get_accessible_upload_boxes(user_id=TEST_USER_ID)
    assert result == []

    # Check with successful status code but garbled response body (not a list)
    httpx_mock.add_response(200, json={"not": "a list"})
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.get_accessible_upload_boxes(user_id=TEST_USER_ID)

    # Check with successful status code but invalid UUID strings
    httpx_mock.add_response(200, json=["invalid-uuid", "another-invalid"])
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.get_accessible_upload_boxes(user_id=TEST_USER_ID)


async def test_check_box_access(config: ConfigFixture, httpx_mock: HTTPXMock):
    """Test the check_box_access function"""
    access_client = AccessClient(config=config.config)

    # Happy path - user has access
    httpx_mock.add_response(200)
    result = await access_client.check_box_access(
        user_id=TEST_USER_ID, box_id=TEST_BOX_ID
    )
    assert result is True

    # Happy path - user does not have access (403)
    httpx_mock.add_response(403, json={"error": "Forbidden"})
    result = await access_client.check_box_access(
        user_id=TEST_USER_ID, box_id=TEST_BOX_ID
    )
    assert result is False

    # Happy path - user does not have access (404)
    httpx_mock.add_response(404, json={"error": "Not found"})
    result = await access_client.check_box_access(
        user_id=TEST_USER_ID, box_id=TEST_BOX_ID
    )
    assert result is False

    # Check unexpected status code
    httpx_mock.add_response(500, json={"error": "Internal server error"})
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.check_box_access(user_id=TEST_USER_ID, box_id=TEST_BOX_ID)

    # Check unexpected status code (different one)
    httpx_mock.add_response(422, json={"error": "Unprocessable entity"})
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.check_box_access(user_id=TEST_USER_ID, box_id=TEST_BOX_ID)

    httpx_mock.add_exception(httpx.RequestError("Network error"))
    with pytest.raises(AccessClient.AccessAPIError):
        await access_client.check_box_access(user_id=TEST_USER_ID, box_id=TEST_BOX_ID)
