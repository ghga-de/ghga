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

"""Unit tests for the file box client"""

from uuid import UUID, uuid4

import pytest
from pytest_httpx import HTTPXMock

from tests.fixtures import ConfigFixture
from uos.adapters.outbound.http import FileBoxClient

pytestmark = pytest.mark.asyncio()

TEST_BOX_ID = UUID("2735c960-5e15-45dc-b27a-59162fbb2fd7")


async def test_create_file_upload_box(config: ConfigFixture, httpx_mock: HTTPXMock):
    """Test the create_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config.config)
    httpx_mock.add_response(201, json=str(TEST_BOX_ID))
    box_id = await file_upload_box_client.create_file_upload_box(storage_alias="HD01")
    assert box_id == TEST_BOX_ID, "Failed happy path"

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.create_file_upload_box(storage_alias="HD01")

    # Check with successful status code but garbled response body
    httpx_mock.add_response(201, json="id123")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.create_file_upload_box(storage_alias="HD01")


async def test_lock_file_upload_box(config: ConfigFixture, httpx_mock: HTTPXMock):
    """Test the lock_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config.config)
    httpx_mock.add_response(204)
    await file_upload_box_client.lock_file_upload_box(
        box_id=TEST_BOX_ID
    )  # no error == success

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.lock_file_upload_box(box_id=TEST_BOX_ID)


async def test_unlock_file_upload_box(config: ConfigFixture, httpx_mock: HTTPXMock):
    """Test the unlock_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config.config)
    httpx_mock.add_response(204)
    await file_upload_box_client.unlock_file_upload_box(
        box_id=TEST_BOX_ID
    )  # no error == success

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.unlock_file_upload_box(box_id=TEST_BOX_ID)


async def test_get_file_upload_list(config: ConfigFixture, httpx_mock: HTTPXMock):
    """Test the get_file_upload_list function"""
    file_upload_box_client = FileBoxClient(config=config.config)
    file_list_response = [uuid4() for _ in range(3)]
    httpx_mock.add_response(200, json=[str(x) for x in file_list_response])
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
