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

"""Unit tests for Work Package operations"""

import asyncio
import base64
from functools import partial

import crypt4gh.keys
import pytest
from pydantic import SecretBytes
from pytest_httpx import HTTPXMock

from ghga_connector import exceptions
from ghga_connector.core.client import async_client
from ghga_connector.core.work_package import WorkPackageClient
from tests.fixtures import set_runtime_test_config  # noqa: F401
from tests.fixtures.mock_api.app import create_caching_headers
from tests.fixtures.utils import (
    PRIVATE_KEY_FILE,
    RecordingClient,
    mock_work_package_token,
    patch_work_package_functions,  # noqa: F401
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.httpx_mock(
        assert_all_responses_were_requested=False,
        can_send_already_matched_responses=True,
        should_mock=lambda request: True,
    ),
]


async def test_get_work_package_file_info(
    httpx_mock: HTTPXMock,
    monkeypatch,
    set_runtime_test_config,  # noqa: F811
):
    """Test response handling with some mock - just make sure code paths work"""
    files = {"file_1": ".tar.gz"}
    private_key = SecretBytes(crypt4gh.keys.get_private_key(PRIVATE_KEY_FILE, ""))
    monkeypatch.setattr(
        "ghga_connector.core.work_package.get_work_package_token",
        mock_work_package_token,
    )

    async with async_client() as client:
        partial_work_pkg_client = partial(
            WorkPackageClient,
            client=client,
            my_private_key=private_key,
            my_public_key=b"",  # doesn't matter for this test
        )

        httpx_mock.add_response(json={"files": files}, status_code=200)

        work_package_client = partial_work_pkg_client()
        response = await work_package_client.get_package_files()
        assert response == files

        httpx_mock.add_response(json={"files": files}, status_code=403)

        with pytest.raises(exceptions.NoWorkPackageAccessError):
            work_package_client = partial_work_pkg_client()
            response = await work_package_client.get_package_files()

        httpx_mock.add_response(json={"files": files}, status_code=500)

        with pytest.raises(exceptions.InvalidWorkPackageResponseError):
            work_package_client = partial_work_pkg_client()
            response = await work_package_client.get_package_files()

        httpx_mock.add_response(json={"files": files}, status_code=501)

        with pytest.raises(exceptions.InvalidWorkPackageResponseError):
            work_package_client = partial_work_pkg_client()
            response = await work_package_client.get_package_files()


async def test_get_work_order_token_caching(
    monkeypatch,
    httpx_mock: HTTPXMock,
    set_runtime_test_config,  # noqa: F811
    patch_work_package_functions,  # noqa: F811
):
    """Test the caching of call to the Work Package API to get a work order token."""
    # Patch the client to record calls
    monkeypatch.setattr(
        "ghga_connector.core.work_package.crypt.decrypt", lambda data, key: "test"
    )
    monkeypatch.setattr("ghga_connector.core.client.httpx.AsyncClient", RecordingClient)
    async with async_client() as client:
        assert isinstance(client, RecordingClient)
        work_pkg_client = WorkPackageClient(
            client=client,
            my_private_key=SecretBytes(b""),
            my_public_key=b"",
        )
        file_id = "file-id-1"
        add_httpx_response = partial(
            httpx_mock.add_response,
            status_code=201,
            json=base64.b64encode(b"1234567890" * 5).decode(),
            headers=create_caching_headers(3),
        )
        add_httpx_response()
        await work_pkg_client.get_download_wot(file_id=file_id)

        # Verify that the call was made
        assert client.calls
        client.assert_last_call_not_from_cache()

        # Make same call and verify that the response came from the cache instead
        await work_pkg_client.get_download_wot(file_id=file_id)
        client.assert_last_call_from_cache()

        # Wait for the cache entry to expire, then make the call again
        await asyncio.sleep(1)
        add_httpx_response()
        await work_pkg_client.get_download_wot(file_id=file_id)
        client.assert_last_call_not_from_cache()
