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

"""Unit tests for Download Client caching"""

import base64
from functools import partial
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretBytes
from pytest_httpx import HTTPXMock

from ghga_connector.core.client import async_client
from ghga_connector.core.downloading.api_calls import DownloadClient
from ghga_connector.core.work_package import WorkPackageClient
from tests.fixtures import set_runtime_test_config  # noqa: F401
from tests.fixtures.utils import (
    RecordingClient,
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

FAKE_DRS_OBJECT = {
    "access_methods": [{"access_url": {"url": "https://test.url"}, "type": "s3"}],
    "id": "test-file-id",
    "size": 1024,
}


async def test_get_drs_object_caching(
    monkeypatch,
    httpx_mock: HTTPXMock,
    set_runtime_test_config,  # noqa: F811
):
    """Test that get_drs_object results are cached and can be invalidated."""
    monkeypatch.setattr("ghga_connector.core.client.httpx.AsyncClient", RecordingClient)
    async with async_client() as client:
        assert isinstance(client, RecordingClient)
        work_pkg_client = Mock()
        work_pkg_client.get_download_wot = AsyncMock(return_value="fake-wot")
        work_pkg_client.make_auth_headers = AsyncMock(return_value=httpx.Headers())

        download_client = DownloadClient(
            client=client, work_package_client=work_pkg_client
        )

        file_id = "test-file-id"
        httpx_mock.add_response(json=FAKE_DRS_OBJECT, status_code=200)

        # First call should hit the network
        await download_client.get_drs_object(file_id)
        assert client.calls
        client.calls.clear()

        # Second call should come from cache
        await download_client.get_drs_object(file_id)
        assert not client.calls, "DRS object should have been provided by the cache"

        # After invalidation, call should hit the network again
        download_client.get_drs_object.cache_invalidate(file_id)
        httpx_mock.add_response(json=FAKE_DRS_OBJECT, status_code=200)
        await download_client.get_drs_object(file_id)
        assert client.calls, "DRS object should NOT have been provided by the cache"


async def test_get_work_order_token_caching(
    monkeypatch,
    httpx_mock: HTTPXMock,
    set_runtime_test_config,  # noqa: F811
    patch_work_package_functions,  # noqa: F811
):
    """Test the caching of call to the Work Package API to get an upload WOT."""
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
        file_id = uuid4()
        add_httpx_response = partial(
            httpx_mock.add_response,
            status_code=201,
            json=base64.b64encode(b"1234567890" * 5).decode(),
        )
        add_httpx_response()
        box_id = uuid4()
        await work_pkg_client.get_upload_wot(
            work_type="upload", file_id=file_id, box_id=box_id
        )

        # Verify that the call was made
        assert client.calls
        client.calls.clear()
        assert not client.calls

        # Make same call and verify that the response came from the cache instead
        await work_pkg_client.get_upload_wot(
            work_type="upload", file_id=file_id, box_id=box_id
        )
        assert not client.calls, "Upload WOT should have been provided by the cache"

        # Manually invalidate the cache, then make the call again
        work_pkg_client.get_upload_wot.cache_invalidate(
            work_type="upload", file_id=file_id, box_id=box_id
        )
        add_httpx_response()
        await work_pkg_client.get_upload_wot(
            work_type="upload", file_id=file_id, box_id=box_id
        )
        assert client.calls, "Upload WOT should NOT have been provided by the cache"
