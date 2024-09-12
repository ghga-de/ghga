# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Tests for API Calls"""

from contextlib import nullcontext
from functools import partial
from pathlib import Path
from typing import Union
from unittest.mock import Mock

import pytest
from pytest_httpx import HTTPXMock

from ghga_connector.core import WKVSCaller
from ghga_connector.core.api_calls import WorkPackageAccessor
from ghga_connector.core.client import async_client
from ghga_connector.core.exceptions import (
    CantChangeUploadStatusError,
    ConnectionFailedError,
    InvalidWPSResponseError,
    MaxPartNoExceededError,
    NoWorkPackageAccessError,
    UploadNotRegisteredError,
    WellKnownValueNotFound,
)
from ghga_connector.core.uploading import Uploader
from ghga_connector.core.uploading.structs import UploadStatus
from tests.fixtures.utils import mock_wps_token


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_url,upload_id,upload_status,expected_exception",
    [
        (False, "pending", UploadStatus.UPLOADED, None),
        (False, "uploaded", UploadStatus.CANCELLED, None),
        (False, "pending", UploadStatus.CANCELLED, CantChangeUploadStatusError),
        (False, "uploadable", UploadStatus.UPLOADED, CantChangeUploadStatusError),
        (False, "not_uploadable", UploadStatus.UPLOADED, UploadNotRegisteredError),
        (True, "uploaded", UploadStatus.UPLOADED, ConnectionFailedError),
    ],
)
async def test_patch_multipart_upload(
    httpx_mock: HTTPXMock,
    bad_url: bool,
    upload_id: str,
    upload_status: UploadStatus,
    expected_exception: type[Union[Exception, None]],
):
    """Test the patch_multipart_upload function"""
    api_url = "http://bad_url" if bad_url else "http://127.0.0.1"
    if bad_url:
        httpx_mock.add_exception(
            exception=ConnectionFailedError(
                url=f"{api_url}/uploads/{upload_id}", reason="Testing"
            )
        )
    elif expected_exception == CantChangeUploadStatusError:
        httpx_mock.add_response(
            status_code=400,
            json={
                "data": {},
                "description": "",
                "exception_id": "uploadNotPending",
            },
        )
    elif expected_exception == UploadNotRegisteredError:
        httpx_mock.add_response(
            status_code=404,
            json={"data": {}, "description": "", "exception_id": "noSuchUpload"},
        )
    elif expected_exception is None:
        httpx_mock.add_response(status_code=204)

    with (
        pytest.raises(
            expected_exception  # type: ignore
        )
        if expected_exception
        else nullcontext()
    ):
        async with async_client() as client:
            uploader = Uploader(
                api_url=api_url, client=client, file_id="", public_key_path=Path("")
            )
            uploader._upload_id = upload_id

            await uploader.patch_multipart_upload(upload_status=upload_status)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "from_part, end_part, expected_exception",
    [
        (None, 10, None),
        (2, 10, None),
        (9999, 10001, MaxPartNoExceededError),
    ],
)
async def test_get_part_upload_urls(
    from_part: Union[int, None],
    end_part: int,
    expected_exception: type[Union[Exception, None]],
):
    """Test the `get_part_upload_urls` generator for iterating through signed part urls"""
    upload_id = "example-upload"
    api_url = "http://my-api.example"
    from_part_ = 1 if from_part is None else from_part

    # mock the function to get a specific part upload url:
    static_signed_url = "http://my-signed-url.example/97982jsdf7823j"
    get_url_func = Mock(return_value=static_signed_url)

    if not from_part:
        from_part = 1

    async with async_client() as client:
        uploader = Uploader(
            api_url=api_url, client=client, file_id="", public_key_path=Path("")
        )
        uploader._upload_id = upload_id

        part_upload_urls = uploader.get_part_upload_urls(
            get_url_func=get_url_func, from_part=from_part
        )

    with (
        pytest.raises(expected_exception)  # type: ignore
        if expected_exception
        else nullcontext()
    ):
        for idx, signed_url in enumerate(part_upload_urls):
            assert static_signed_url == signed_url

            part_no = idx + from_part_
            get_url_func.assert_called_with(
                api_url=api_url, upload_id=upload_id, part_no=part_no
            )

            if part_no >= end_part:
                break


@pytest.mark.asyncio
async def test_get_wps_file_info(httpx_mock: HTTPXMock):
    """Test response handling with some mock - just make sure code paths work"""
    files = {"file_1": ".tar.gz"}

    async with async_client() as client:
        partial_accessor = partial(
            WorkPackageAccessor,
            api_url="http://127.0.0.1",
            client=client,
            dcs_api_url="",
            my_private_key=b"",
            my_public_key=b"",
        )

        httpx_mock.add_response(json={"files": files}, status_code=200)
        wp_id, wp_token = mock_wps_token(1, None)
        work_package_accessor = partial_accessor(
            access_token=wp_token,
            package_id=wp_id,
        )
        response = await work_package_accessor.get_package_files()
        assert response == files

        httpx_mock.add_response(json={"files": files}, status_code=403)

        with pytest.raises(NoWorkPackageAccessError):
            wp_id, wp_token = mock_wps_token(1, None)
            work_package_accessor = partial_accessor(
                access_token=wp_token,
                package_id=wp_id,
            )
            response = await work_package_accessor.get_package_files()

        httpx_mock.add_response(json={"files": files}, status_code=500)

        with pytest.raises(InvalidWPSResponseError):
            wp_id, wp_token = mock_wps_token(1, None)
            work_package_accessor = partial_accessor(
                access_token=wp_token,
                package_id=wp_id,
            )
            response = await work_package_accessor.get_package_files()

        httpx_mock.add_response(json={"files": files}, status_code=501)

        with pytest.raises(InvalidWPSResponseError):
            wp_id, wp_token = mock_wps_token(1, None)
            work_package_accessor = partial_accessor(
                access_token=wp_token,
                package_id=wp_id,
            )
            response = await work_package_accessor.get_package_files()


@pytest.mark.asyncio
async def test_wkvs_calls(httpx_mock: HTTPXMock):
    """Test handling of responses for WKVS api calls"""
    wkvs_url = "https://127.0.0.1"

    async with async_client() as client:
        wkvs_caller = WKVSCaller(client=client, wkvs_url=wkvs_url)

        with pytest.raises(WellKnownValueNotFound):
            httpx_mock.add_response(status_code=404)
            await wkvs_caller.get_server_pubkey()

        with pytest.raises(KeyError):
            httpx_mock.add_response(status_code=200, json={})
            await wkvs_caller.get_server_pubkey()

        # test each call to CYA
        for func, value_name in [
            (wkvs_caller.get_dcs_api_url, "dcs_api_url"),
            (wkvs_caller.get_server_pubkey, "crypt4gh_public_key"),
            (wkvs_caller.get_ucs_api_url, "ucs_api_url"),
            (wkvs_caller.get_wps_api_url, "wps_api_url"),
        ]:
            httpx_mock.add_response(json={value_name: "dummy-value"})
            value = await func()
            assert value == "dummy-value"
