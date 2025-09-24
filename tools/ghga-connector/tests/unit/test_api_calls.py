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

"""Tests for API Calls"""

import asyncio
import base64
from contextlib import nullcontext
from functools import partial
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from pytest_httpx import HTTPXMock

from ghga_connector.core import WorkPackageAccessor, async_client, exceptions
from ghga_connector.core.api_calls.well_knowns import WKVSCaller
from ghga_connector.core.uploading.structs import UploadStatus
from ghga_connector.core.uploading.uploader import Uploader
from tests.fixtures.mock_api.app import create_caching_headers
from tests.fixtures.utils import mock_wps_token

pytest.mark.httpx_mock(
    assert_all_responses_were_requested=False, can_send_already_matched_responses=True
)
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.httpx_mock(
        assert_all_responses_were_requested=False,
        can_send_already_matched_responses=True,
        should_mock=lambda request: True,
    ),
]
API_URL = "http://127.0.0.1"


class RecordingClient(httpx.AsyncClient):
    """An `AsyncClient` wrapper that records responses."""

    calls: list[httpx.Response]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    async def _do_request(self, method: str, *args, **kwargs) -> httpx.Response:
        """Wrap actual client calls so we can see which calls were cached vs not."""
        method_func = getattr(super(), method)
        response = await method_func(*args, **kwargs)
        self.calls.append(response)
        return response

    def assert_last_call_from_cache(self):
        """Assert that the last call was from the cache."""
        assert self.calls[-1].extensions["from_cache"]

    def assert_last_call_not_from_cache(self):
        """Assert that the last call was not from the cache."""
        assert not self.calls[-1].extensions["from_cache"]

    async def get(self, *args, **kwargs) -> httpx.Response:
        """Record GET calls."""
        return await self._do_request("get", *args, **kwargs)

    async def post(self, *args, **kwargs) -> httpx.Response:
        """Record POST calls."""
        return await self._do_request("post", *args, **kwargs)


async def test_get_work_order_token_caching(monkeypatch, httpx_mock: HTTPXMock):
    """Test the caching of call to the WPS to get a work order token.

    The `mock_external_calls` fixture will route HTTP requests to the mock API.
    """
    # Patch the decrypt function so we don't need an actual token
    monkeypatch.setattr(
        "ghga_connector.core.work_package._decrypt", lambda data, key: data
    )

    # Patch the client to record calls
    monkeypatch.setattr("ghga_connector.core.client.httpx.AsyncClient", RecordingClient)
    async with async_client() as client:
        assert isinstance(client, RecordingClient)
        accessor = WorkPackageAccessor(
            api_url=API_URL,
            client=client,
            dcs_api_url="",
            my_private_key=b"",
            my_public_key=b"",
            access_token="",
            package_id="wp_1",
        )
        file_id = "file-id-1"
        add_httpx_response = partial(
            httpx_mock.add_response,
            status_code=201,
            json=base64.b64encode(b"1234567890" * 5).decode(),
            headers=create_caching_headers(3),
        )
        add_httpx_response()
        await accessor.get_work_order_token(file_id=file_id)

        # Verify that the call was made
        assert client.calls
        client.assert_last_call_not_from_cache()

        # Make same call and verify that the response came from the cache instead
        await accessor.get_work_order_token(file_id=file_id)
        client.assert_last_call_from_cache()

        # Wait for the cache entry to expire, then make the call again
        await asyncio.sleep(1)
        add_httpx_response()
        await accessor.get_work_order_token(file_id=file_id)
        client.assert_last_call_not_from_cache()


@pytest.mark.parametrize(
    "bad_url,upload_id,upload_status,expected_exception",
    [
        (False, "pending", UploadStatus.UPLOADED, None),
        (False, "uploaded", UploadStatus.CANCELLED, None),
        (
            False,
            "pending",
            UploadStatus.CANCELLED,
            exceptions.CantChangeUploadStatusError,
        ),
        (
            False,
            "uploadable",
            UploadStatus.UPLOADED,
            exceptions.CantChangeUploadStatusError,
        ),
        (
            False,
            "not_uploadable",
            UploadStatus.UPLOADED,
            exceptions.UploadNotRegisteredError,
        ),
        (True, "uploaded", UploadStatus.UPLOADED, exceptions.ConnectionFailedError),
    ],
)
async def test_patch_multipart_upload(
    httpx_mock: HTTPXMock,
    bad_url: bool,
    upload_id: str,
    upload_status: UploadStatus,
    expected_exception: type[Exception | None],
):
    """Test the patch_multipart_upload function"""
    api_url = "http://bad_url" if bad_url else "http://127.0.0.1"
    if bad_url:
        httpx_mock.add_exception(
            exception=exceptions.ConnectionFailedError(
                url=f"{api_url}/uploads/{upload_id}", reason="Testing"
            )
        )
    elif expected_exception == exceptions.CantChangeUploadStatusError:
        httpx_mock.add_response(
            status_code=400,
            json={
                "data": {},
                "description": "",
                "exception_id": "uploadNotPending",
            },
        )
    elif expected_exception == exceptions.UploadNotRegisteredError:
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


@pytest.mark.parametrize(
    "from_part, end_part, expected_exception",
    [
        (None, 10, None),
        (2, 10, None),
        (9999, 10001, exceptions.MaxPartNoExceededError),
    ],
)
async def test_get_part_upload_urls(
    from_part: int | None,
    end_part: int,
    expected_exception: type[Exception | None],
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

        with pytest.raises(exceptions.NoWorkPackageAccessError):
            wp_id, wp_token = mock_wps_token(1, None)
            work_package_accessor = partial_accessor(
                access_token=wp_token,
                package_id=wp_id,
            )
            response = await work_package_accessor.get_package_files()

        httpx_mock.add_response(json={"files": files}, status_code=500)

        with pytest.raises(exceptions.InvalidWPSResponseError):
            wp_id, wp_token = mock_wps_token(1, None)
            work_package_accessor = partial_accessor(
                access_token=wp_token,
                package_id=wp_id,
            )
            response = await work_package_accessor.get_package_files()

        httpx_mock.add_response(json={"files": files}, status_code=501)

        with pytest.raises(exceptions.InvalidWPSResponseError):
            wp_id, wp_token = mock_wps_token(1, None)
            work_package_accessor = partial_accessor(
                access_token=wp_token,
                package_id=wp_id,
            )
            response = await work_package_accessor.get_package_files()


async def test_wkvs_calls(httpx_mock: HTTPXMock):
    """Test handling of responses for WKVS api calls"""
    wkvs_url = "https://127.0.0.1"

    async with async_client() as client:
        wkvs_caller = WKVSCaller(client=client, wkvs_url=wkvs_url)

        with pytest.raises(exceptions.WellKnownValueNotFound):
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
