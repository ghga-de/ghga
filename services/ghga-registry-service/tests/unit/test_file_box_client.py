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

"""Unit tests for the file box client"""

import json
from uuid import UUID, uuid4

import httpx
import pytest
from ghga_service_commons.utils.jwt_helpers import decode_and_validate_token
from hexkit.utils import now_utc_ms_prec
from jwcrypto.jwk import JWK
from pytest_httpx import HTTPXMock

from rs.adapters.outbound.http import FileBoxClient
from rs.config import Config
from rs.core.models import FileUploadWithAccession
from tests.fixtures.utils import TEST_MAX_SIZE

pytestmark = pytest.mark.asyncio

TEST_BOX_ID = UUID("2735c960-5e15-45dc-b27a-59162fbb2fd7")


async def test_create_file_upload_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the create_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(201, json=str(TEST_BOX_ID))
    box_id = await file_upload_box_client.create_file_upload_box(
        storage_alias="HD01", max_size=TEST_MAX_SIZE
    )
    assert box_id == TEST_BOX_ID, "Failed happy path"

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.create_file_upload_box(
            storage_alias="HD01", max_size=TEST_MAX_SIZE
        )

    # Check with successful status code but garbled response body
    httpx_mock.add_response(201, json="id123")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.create_file_upload_box(
            storage_alias="HD01", max_size=TEST_MAX_SIZE
        )


async def test_lock_file_upload_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the lock_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(204)
    await file_upload_box_client.lock_file_upload_box(
        box_id=TEST_BOX_ID, version=0
    )  # no error == success
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "version": 0,
        "state": "locked",
    }

    httpx_mock.add_response(409, json="Box out of date")
    with pytest.raises(FileBoxClient.FUBVersionError):
        await file_upload_box_client.lock_file_upload_box(box_id=TEST_BOX_ID, version=0)

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.lock_file_upload_box(box_id=TEST_BOX_ID, version=0)


async def test_unlock_file_upload_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the unlock_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(204)
    await file_upload_box_client.unlock_file_upload_box(
        box_id=TEST_BOX_ID, version=0
    )  # no error == success
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "version": 0,
        "state": "open",
    }

    httpx_mock.add_response(409, json="Box out of date")
    with pytest.raises(FileBoxClient.FUBVersionError):
        await file_upload_box_client.unlock_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.unlock_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )


async def test_get_file_upload_list(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the get_file_upload_list function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    file_list_response = [
        FileUploadWithAccession(
            id=uuid4(),
            box_id=uuid4(),
            storage_alias="HD01",
            bucket_id="permanent",
            object_id=uuid4(),
            alias=f"test{i}",
            decrypted_sha256=f"checksum{i}",
            decrypted_size=1000 + i * 100,
            encrypted_size=1100 + i * 100,
            state="archived",
            state_updated=now_utc_ms_prec(),
            part_size=100,
        )
        for i in range(3)
    ]
    httpx_mock.add_response(
        200, json=[x.model_dump(mode="json") for x in file_list_response]
    )
    file_list = await file_upload_box_client.get_file_upload_list(box_id=TEST_BOX_ID)
    assert file_list == file_list_response

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.get_file_upload_list(box_id=TEST_BOX_ID)

    # Check with successful status code but garbled response body
    httpx_mock.add_response(200, json="id123")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.get_file_upload_list(box_id=TEST_BOX_ID)

    # Check with empty list response
    httpx_mock.add_response(200, json=[])
    file_list = await file_upload_box_client.get_file_upload_list(box_id=TEST_BOX_ID)
    assert file_list == []


async def test_archive_file_upload_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the archive_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(204)
    await file_upload_box_client.archive_file_upload_box(
        box_id=TEST_BOX_ID, version=0
    )  # no error == success
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "version": 0,
        "state": "archived",
    }

    httpx_mock.add_response(409, json="Box out of date")
    with pytest.raises(FileBoxClient.FUBVersionError):
        await file_upload_box_client.archive_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.archive_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )


async def test_resize_file_upload_box(
    config: Config,
    httpx_mock: HTTPXMock,
    httpx_client: httpx.AsyncClient,
    work_order_jwk: JWK,
):
    """Test the resize_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)

    # Happy path - verify request body and WOT work_type/box_id
    httpx_mock.add_response(204)
    await file_upload_box_client.resize_file_upload_box(
        box_id=TEST_BOX_ID, version=0, max_size=TEST_MAX_SIZE
    )
    request = httpx_mock.get_requests()[0]
    assert json.loads(request.content) == {"version": 0, "max_size": TEST_MAX_SIZE}

    raw_token = request.headers["authorization"].removeprefix("Bearer ")
    wot_claims = decode_and_validate_token(raw_token, work_order_jwk)
    assert wot_claims["work_type"] == "resize"
    assert wot_claims["box_id"] == str(TEST_BOX_ID)

    # Make sure 409 "boxVersionOutdated" is translated as FUBVersionError
    httpx_mock.add_response(409, json={"exception_id": "boxVersionOutdated"})
    with pytest.raises(FileBoxClient.FUBVersionError):
        await file_upload_box_client.resize_file_upload_box(
            box_id=TEST_BOX_ID, version=0, max_size=TEST_MAX_SIZE
        )

    # Make sure 409 "boxMaxSizeTooLow" is translated as FUBMaxSizeTooLowError
    httpx_mock.add_response(409, json={"exception_id": "boxMaxSizeTooLow"})
    with pytest.raises(FileBoxClient.FUBMaxSizeTooLowError):
        await file_upload_box_client.resize_file_upload_box(
            box_id=TEST_BOX_ID, version=0, max_size=1
        )

    # Make sure any other non-204 response is translated as OperationError
    httpx_mock.add_response(500, json={"exception_id": "miscError"})
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.resize_file_upload_box(
            box_id=TEST_BOX_ID, version=0, max_size=TEST_MAX_SIZE
        )


async def test_delete_file_upload(
    config: Config,
    httpx_mock: HTTPXMock,
    httpx_client: httpx.AsyncClient,
    work_order_jwk: JWK,
):
    """Test the delete_file_upload function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    test_file_id = uuid4()

    # Happy path - verify WOT work_type/box_id/file_id
    httpx_mock.add_response(204)
    await file_upload_box_client.delete_file_upload(
        box_id=TEST_BOX_ID, file_id=test_file_id
    )  # no error == success
    request = httpx_mock.get_requests()[0]
    raw_token = request.headers["authorization"].removeprefix("Bearer ")
    wot_claims = decode_and_validate_token(raw_token, work_order_jwk)
    assert wot_claims["work_type"] == "delete"
    assert wot_claims["box_id"] == str(TEST_BOX_ID)
    assert wot_claims["file_id"] == str(test_file_id)

    # Make sure 409/boxStateError is translated as FUBLockedError
    httpx_mock.add_response(409, json={"exception_id": "boxStateError"})
    with pytest.raises(FileBoxClient.FUBLockedError):
        await file_upload_box_client.delete_file_upload(
            box_id=TEST_BOX_ID, file_id=test_file_id
        )

    # Make sure 400, 404, and 500 are translated as OperationError
    for status_code in (400, 404, 500):
        httpx_mock.add_response(status_code, json="Some error occurred.")
        with pytest.raises(FileBoxClient.OperationError):
            await file_upload_box_client.delete_file_upload(
                box_id=TEST_BOX_ID, file_id=test_file_id
            )
