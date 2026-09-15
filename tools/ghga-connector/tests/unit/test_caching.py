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

from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx2
import pytest
from pydantic import SecretBytes

from ghga_connector.core.client import async_client
from ghga_connector.core.downloading.api_calls import DownloadClient
from ghga_connector.core.downloading.structs import RetryResponse
from ghga_connector.core.work_package import WorkPackageClient
from ghga_service_commons.api.mock_api import respond
from tests.fixtures import set_runtime_test_config  # noqa: F401
from tests.fixtures.mock_api.apis import (
    DRS_OBJECT,
    DownloadApiMock,
    MockApis,
    WorkPackageApiMock,
    mock_apis,  # noqa: F401
)
from tests.fixtures.utils import (
    RecordingClient,
    patch_work_package_functions,  # noqa: F401
)

pytestmark = [pytest.mark.asyncio]


@pytest.fixture()
def download_api(
    mock_apis: MockApis,  # noqa: F811
    set_runtime_test_config,  # noqa: F811
) -> DownloadApiMock:
    """The Download API mock, with the connector pointed at it."""
    return mock_apis.download


@pytest.fixture()
def work_package_api(
    mock_apis: MockApis,  # noqa: F811
    set_runtime_test_config,  # noqa: F811
) -> WorkPackageApiMock:
    """The Work Package API mock, with the connector pointed at it."""
    return mock_apis.work_package


async def test_get_drs_object_caching(
    monkeypatch,
    download_api: DownloadApiMock,
):
    """Test that get_drs_object results are cached and can be invalidated."""
    monkeypatch.setattr(
        "ghga_connector.core.client.httpx2.AsyncClient", RecordingClient
    )
    download_api.on_get_drs_object = respond(200, json=DRS_OBJECT)

    async with async_client(purpose="download") as client:
        assert isinstance(client, RecordingClient)
        work_pkg_client = Mock()
        work_pkg_client.get_download_wot = AsyncMock(return_value="fake-wot")
        work_pkg_client.make_auth_headers = AsyncMock(return_value=httpx2.Headers())

        download_client = DownloadClient(
            client=client, work_package_client=work_pkg_client
        )

        file_id = "test-file-id"

        # First call should hit the network
        await download_client.get_drs_object(file_id)
        assert client.calls
        client.calls.clear()

        # Second call should come from cache
        await download_client.get_drs_object(file_id)
        assert not client.calls, "DRS object should have been provided by the cache"

        # After invalidation, call should hit the network again
        download_client.get_drs_object.cache_invalidate(file_id)
        await download_client.get_drs_object(file_id)
        assert client.calls, "DRS object should NOT have been provided by the cache"


async def test_retry_response_is_not_cached(
    monkeypatch,
    download_api: DownloadApiMock,
):
    """Test that we don't serve 202/retry-after from the cache.

    Regression test: previously the cached RetryResponse stuck around for the whole
    cache TTL, so the staging poll loop kept reporting the file as "being staged" even
    after it had actually been staged.
    """
    monkeypatch.setattr(
        "ghga_connector.core.client.httpx2.AsyncClient", RecordingClient
    )

    # The file finishes staging between the first and the second poll. Neither status
    # code is retryable, so each poll consumes exactly one of these responses.
    polls = iter(
        [
            httpx2.Response(202, headers={"retry-after": "1"}),
            httpx2.Response(200, json=DRS_OBJECT),
        ]
    )

    def poll(request: httpx2.Request, **path_variables: Any) -> httpx2.Response:
        """Report the file as still staging on the first poll, staged on the second."""
        return next(polls)

    download_api.on_get_drs_object = poll

    async with async_client(purpose="download") as client:
        assert isinstance(client, RecordingClient)
        work_pkg_client = Mock()
        work_pkg_client.get_download_wot = AsyncMock(return_value="fake-wot")
        work_pkg_client.make_auth_headers = AsyncMock(return_value=httpx2.Headers())

        download_client = DownloadClient(
            client=client, work_package_client=work_pkg_client
        )

        file_id = "test-file-id"

        # First poll: file is still being staged -> 202 with a retry-after header
        response = await download_client.get_drs_object(file_id)

        assert isinstance(response, RetryResponse)
        assert client.calls

        # The staging loop invalidates the cache on a RetryResponse so subsequent polls
        #  query the live API again.
        download_client.get_drs_object.cache_invalidate(file_id)
        client.calls.clear()

        # Second poll: the file is now staged -> the live API must be hit and the fresh
        #  DRS object returned, NOT the cached RetryResponse.
        response = await download_client.get_drs_object(file_id)
        assert client.calls, "Second poll should hit the network, not the stale cache"
        assert response == DRS_OBJECT


async def test_get_work_order_token_caching(
    monkeypatch,
    work_package_api: WorkPackageApiMock,
    patch_work_package_functions,  # noqa: F811
):
    """Test the caching of call to the Work Package API to get an upload WOT."""
    # Patch the client to record calls
    monkeypatch.setattr(
        "ghga_connector.core.work_package.crypt.decrypt", lambda data, key: "test"
    )
    monkeypatch.setattr(
        "ghga_connector.core.client.httpx2.AsyncClient", RecordingClient
    )

    async with async_client(purpose="upload") as client:
        assert isinstance(client, RecordingClient)
        work_pkg_client = WorkPackageClient(
            client=client,
            my_private_key=SecretBytes(b""),
            my_public_key=b"",
        )
        file_id = uuid4()
        rdub_id = uuid4()
        await work_pkg_client.get_upload_wot(
            work_type="upload", file_id=file_id, research_data_upload_box_id=rdub_id
        )

        # Verify that the call was made
        assert client.calls
        client.calls.clear()
        assert not client.calls

        # Make same call and verify that the response came from the cache instead
        await work_pkg_client.get_upload_wot(
            work_type="upload", file_id=file_id, research_data_upload_box_id=rdub_id
        )
        assert not client.calls, "Upload WOT should have been provided by the cache"

        # Manually invalidate the cache, then make the call again
        work_pkg_client.get_upload_wot.cache_invalidate(
            work_type="upload", file_id=file_id, research_data_upload_box_id=rdub_id
        )
        await work_pkg_client.get_upload_wot(
            work_type="upload", file_id=file_id, research_data_upload_box_id=rdub_id
        )
        assert client.calls, "Upload WOT should NOT have been provided by the cache"
