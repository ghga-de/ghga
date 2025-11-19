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

"""Unit tests for the client for the Upload API"""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import Response
from pydantic import UUID4
from pytest_httpx import HTTPXMock

from ghga_connector import exceptions
from ghga_connector.core.client import async_client
from ghga_connector.core.uploading.api_calls import UploadClient
from tests.fixtures import set_runtime_test_config  # noqa: F401

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.httpx_mock(
        assert_all_responses_were_requested=False,
        can_send_already_matched_responses=True,
        should_mock=lambda request: True,
    ),
]

BOX_ID = UUID("6ec579af-3918-45d2-8333-d2cdcfb53d1d")
FILE_ID = UUID("550e8400-e29b-41d4-a716-446655440002")
FILE_ALIAS = "test-file-1"
UPLOAD_URL = "http://upload_url"


@pytest_asyncio.fixture()
async def upload_client(
    set_runtime_test_config,  # noqa: F811
    monkeypatch,
) -> AsyncGenerator[UploadClient, None]:
    """Create a configured UploadClient.

    The WPAT user input is patched, and the Upload API health
    check is also patched to always return True.
    """
    mock_work_package_client = AsyncMock()
    mock_work_package_client.get_upload_wot.return_value = "wot"
    mock_work_package_client.get_package_box_id.return_value = BOX_ID
    box_id_mock = AsyncMock()
    box_id_mock.return_value = BOX_ID
    monkeypatch.setattr(
        "ghga_connector.core.work_package.WorkPackageClient.get_package_box_id",
        box_id_mock,
    )

    monkeypatch.setattr(
        "ghga_connector.core.uploading.api_calls.is_service_healthy", lambda s: True
    )
    async with async_client() as client:
        yield UploadClient(client=client, work_package_client=mock_work_package_client)


async def test_create_file_upload_success(
    upload_client: UploadClient, httpx_mock: HTTPXMock
):
    """Test the create_file_upload() method on the UploadClient"""
    url = f"{upload_client._upload_api_url}/boxes/{BOX_ID}/uploads"
    body = {"alias": FILE_ALIAS, "size": 5}

    httpx_mock.add_response(
        201, url=url, match_json=body, method="POST", json=str(FILE_ID)
    )
    file_id = await upload_client.create_file_upload(file_alias=FILE_ALIAS, file_size=5)
    assert file_id == FILE_ID

    # Check that we get the right type of WOT
    upload_client._work_package_client.get_upload_wot.assert_called_with(  # type: ignore
        work_type="create", box_id=BOX_ID, file_id=None, alias=FILE_ALIAS
    )

    # Test that other status codes will trigger the error translation
    httpx_mock.add_response(500, url=url, match_json=body, method="POST")
    with pytest.raises(exceptions.UnexpectedError):
        _ = await upload_client.create_file_upload(file_alias=FILE_ALIAS, file_size=5)


async def test_get_part_upload_url(upload_client: UploadClient, httpx_mock: HTTPXMock):
    """Test the get_part_upload_url() method on the UploadClient"""
    url = f"{upload_client._upload_api_url}/boxes/{BOX_ID}/uploads/{FILE_ID}/parts/1"
    httpx_mock.add_response(200, url=url, method="GET", json=UPLOAD_URL)
    upload_url = await upload_client.get_part_upload_url(file_id=FILE_ID, part_no=1)
    assert upload_url == UPLOAD_URL

    # Check that we get the right type of WOT
    upload_client._work_package_client.get_upload_wot.assert_called_with(  # type: ignore
        work_type="upload", box_id=BOX_ID, file_id=FILE_ID, alias=None
    )

    # Test that other status codes will trigger the error translation
    httpx_mock.add_response(500, url=url, method="GET", json=UPLOAD_URL)
    with pytest.raises(exceptions.UnexpectedError):
        _ = await upload_client.get_part_upload_url(file_id=FILE_ID, part_no=1)


async def test_upload_file_part(upload_client: UploadClient, httpx_mock: HTTPXMock):
    """Test the upload_file_part() method on the UploadClient"""
    url = f"{upload_client._upload_api_url}/boxes/{BOX_ID}/uploads/{FILE_ID}/parts/1"
    httpx_mock.add_response(200, url=url, method="GET", json=UPLOAD_URL)
    httpx_mock.add_response(200, url=UPLOAD_URL, method="PUT", match_content=b"abc123")
    await upload_client.upload_file_part(file_id=FILE_ID, content=b"abc123", part_no=1)


async def test_complete_file_upload(upload_client: UploadClient, httpx_mock: HTTPXMock):
    """Test the complete_file_upload() method on the UploadClient"""
    url = f"{upload_client._upload_api_url}/boxes/{BOX_ID}/uploads/{FILE_ID}"
    unencrypted_checksum = "abc123"
    encrypted_checksum = "xyz456"
    body = {
        "unencrypted_checksum": unencrypted_checksum,
        "encrypted_checksum": encrypted_checksum,
    }
    httpx_mock.add_response(204, url=url, match_json=body, method="PATCH")
    await upload_client.complete_file_upload(
        file_id=FILE_ID,
        unencrypted_checksum=unencrypted_checksum,
        encrypted_checksum=encrypted_checksum,
    )

    # Check that we get the right type of WOT
    upload_client._work_package_client.get_upload_wot.assert_called_with(  # type: ignore
        work_type="close", box_id=BOX_ID, file_id=FILE_ID, alias=None
    )

    # Test that other status codes will trigger the error translation
    httpx_mock.add_response(500, url=url, match_json=body, method="PATCH")
    with pytest.raises(exceptions.UnexpectedError):
        await upload_client.complete_file_upload(
            file_id=FILE_ID,
            unencrypted_checksum=unencrypted_checksum,
            encrypted_checksum=encrypted_checksum,
        )


async def test_delete_file(upload_client: UploadClient, httpx_mock: HTTPXMock):
    """Test the delete_file() method on the UploadClient"""
    url = f"{upload_client._upload_api_url}/boxes/{BOX_ID}/uploads/{FILE_ID}"
    httpx_mock.add_response(204, url=url, method="DELETE")
    await upload_client.delete_file(file_id=FILE_ID)

    # Check that we get the right type of WOT
    upload_client._work_package_client.get_upload_wot.assert_called_with(  # type: ignore
        work_type="delete", box_id=BOX_ID, file_id=FILE_ID, alias=None
    )

    # Test that other status codes will trigger the error translation
    httpx_mock.add_response(500, url=url)
    with pytest.raises(exceptions.UnexpectedError):
        await upload_client.delete_file(file_id=FILE_ID)


@pytest.mark.parametrize(
    "status_code, response_json, box_id, file_alias, file_id, expected_error",
    [
        # 400 status code
        (
            400,
            {"exception_id": "s3StorageError"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.S3StorageError,
        ),
        # 401 status code
        (
            401,
            {"exception_id": "authorizationError"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.AuthorizationError,
        ),
        # 403 status code
        (
            403,
            {"exception_id": "authorizationError"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.AuthorizationError,
        ),
        # 404 status codes - boxNotFound
        (
            404,
            {"exception_id": "boxNotFound"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.InvalidBoxError,
        ),
        # 404 status codes - fileUploadNotFound
        (
            404,
            {"exception_id": "fileUploadNotFound"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.InvalidFileUploadError,
        ),
        # 404 status codes - s3UploadDetailsNotFound
        (
            404,
            {"exception_id": "s3UploadDetailsNotFound"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.S3UploadDetailsError,
        ),
        # 404 status codes - s3UploadNotFound
        (
            404,
            {"exception_id": "s3UploadNotFound"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.S3UploadMissingError,
        ),
        # 404 status codes - no matching exception id
        (
            404,
            {"exception_id": "nosuchexceptionid"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.UnexpectedError,
        ),
        # 409 status codes - lockedBox
        (
            409,
            {"exception_id": "lockedBox"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.UploadBoxLockedError,
        ),
        # 409 status codes - fileUploadAlreadyExists
        (
            409,
            {"exception_id": "fileUploadAlreadyExists"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.UploadAlreadyExistsError,
        ),
        # 409 status codes - orphanedMultipartUpload
        (
            409,
            {"exception_id": "orphanedMultipartUpload"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.OrphanedUploadError,
        ),
        # 409 status codes - no matching exception id
        (
            409,
            {"exception_id": "nosuchexceptionid"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.UnexpectedError,
        ),
        # Unexpected status code
        (
            500,
            {"exception_id": "internalServerError"},
            BOX_ID,
            FILE_ALIAS,
            FILE_ID,
            exceptions.UnexpectedError,
        ),
        # Test with None values for optional parameters - 404 boxNotFound
        (
            404,
            {"exception_id": "boxNotFound"},
            None,
            None,
            None,
            exceptions.InvalidBoxError,
        ),
        # Test with None values for optional parameters - 409 lockedBox
        (
            409,
            {"exception_id": "lockedBox"},
            None,
            None,
            None,
            exceptions.UploadBoxLockedError,
        ),
        # Test with partial None values - file_alias None, others present
        (
            404,
            {"exception_id": "fileUploadNotFound"},
            BOX_ID,
            None,
            FILE_ID,
            exceptions.InvalidFileUploadError,
        ),
        # Test with partial None values - file_id None, others present
        (
            409,
            {"exception_id": "orphanedMultipartUpload"},
            BOX_ID,
            FILE_ALIAS,
            None,
            exceptions.OrphanedUploadError,
        ),
    ],
)
async def test_handle_bad_status_codes(
    upload_client: UploadClient,
    status_code: int,
    response_json: dict[str, Any],
    box_id: UUID4 | None,
    file_alias: str | None,
    file_id: UUID4 | None,
    expected_error: type[Exception],
):
    """Test _handle_bad_status_codes method with various parameters and status codes."""
    response = Response(status_code=status_code, json=response_json)
    with pytest.raises(expected_error):
        upload_client._handle_bad_status_codes(
            status_code=status_code,
            response=response,
            box_id=box_id,
            file_alias=file_alias,
            file_id=file_id,
        )
