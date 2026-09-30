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
#

"""Mocks of the APIs the connector calls, all served by the `mock_apis` fixture.

Assert on what the connector sent via a mock's `requests` after the call, not inside a
handler, where a failed assertion would surface as a request error.
"""

import base64
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx2
import pytest

from ghga_service_commons.http.mock_api import MockApi, ResponseHandler, respond, serve
from ghga_service_commons.utils.utc_dates import now_as_utc
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.router import (
    MOCK_API_HOST,
    MockApiTransport,
    httpyexpect_error,
    path_variables,
)
from tests.fixtures.utils import TEST_FILE_ID, TEST_PUBLIC_KEYS, TEST_STORAGE_ALIAS1

__all__ = [
    "DOWNLOAD_API_URL",
    "DRS_OBJECT",
    "PART_PATH",
    "UPLOAD_API_URL",
    "UPLOAD_PATH",
    "UPLOAD_URL",
    "WORK_ORDER_TOKEN",
    "WORK_PACKAGE_API_URL",
    "DownloadApiMock",
    "MockApis",
    "StagedObject",
    "StorageMock",
    "UploadApiMock",
    "WkvsMock",
    "WorkPackageApiMock",
    "mock_apis",
]

# Where the mocked APIs live; the test config and the WKVS mock name the same URLs
UPLOAD_API_URL = f"http://{MOCK_API_HOST}/upload"
DOWNLOAD_API_URL = f"http://{MOCK_API_HOST}/download"
WORK_PACKAGE_API_URL = f"http://{MOCK_API_HOST}/work"
# Stands in for object storage; the presigned URLs the mocks hand out live under here
STORAGE_URL = f"http://{MOCK_API_HOST}/storage"

# A request under one of these goes to the mocks, see `MockApiTransport`
MOCKED_BASE_URLS = (
    get_test_config().wkvs_api_url,
    UPLOAD_API_URL,
    DOWNLOAD_API_URL,
    WORK_PACKAGE_API_URL,
    STORAGE_URL,
)


# Upload API paths, relative to `UPLOAD_API_URL`
UPLOADS_PATH = "/boxes/{box_id}/uploads"
UPLOAD_PATH = f"{UPLOADS_PATH}/{{file_id}}"
PART_PATH = f"{UPLOAD_PATH}/parts/{{part_no}}"
# The presigned URL the Upload API hands out for a part by default
UPLOAD_URL = f"{STORAGE_URL}/part"
EMPTY_LISTING: dict[str, Any] = {"items": [], "total_count": 0}


def _created_file_upload(request: httpx2.Request) -> httpx2.Response:
    """Report the upload as created, echoing the alias the connector checks."""
    return httpx2.Response(
        201,
        json={
            "file_id": str(TEST_FILE_ID),
            "alias": json.loads(request.read())["alias"],
            "storage_alias": TEST_STORAGE_ALIAS1,
        },
    )


class UploadApiMock(MockApi):
    """A mock of the Upload API endpoints the connector calls, succeeding by default."""

    def __init__(self, base_url: str = UPLOAD_API_URL) -> None:
        super().__init__(base_url)
        self.on_create_file_upload: ResponseHandler = _created_file_upload
        self.on_get_box_uploads: ResponseHandler = respond(200, json=EMPTY_LISTING)
        self.on_get_part_upload_url: ResponseHandler = respond(200, json=UPLOAD_URL)
        self.on_complete_file_upload: ResponseHandler = respond(204)
        self.on_delete_file: ResponseHandler = respond(204)
        self.route("POST", UPLOADS_PATH, "on_create_file_upload")
        self.route("GET", UPLOADS_PATH, "on_get_box_uploads")
        self.route("GET", PART_PATH, "on_get_part_upload_url")
        self.route("PATCH", UPLOAD_PATH, "on_complete_file_upload")
        self.route("DELETE", UPLOAD_PATH, "on_delete_file")


# Work Package API paths, relative to `WORK_PACKAGE_API_URL`
WORK_PACKAGE_PATH = "/work-packages/{package_id}"
UPLOAD_WOT_PATH = f"{WORK_PACKAGE_PATH}/boxes/{{box_id}}/work-order-tokens"
DOWNLOAD_WOT_PATH = f"{WORK_PACKAGE_PATH}/files/{{file_id}}/work-order-tokens"

# The WPS's encrypted token; `_decrypt` is patched to the identity, so it is the bearer
WORK_ORDER_TOKEN = base64.b64encode(b"1234567890" * 5).decode()


def _upload_work_order_token(request: httpx2.Request) -> httpx2.Response:
    """Hand out a token naming what it authorizes, since it travels as the bearer."""
    body = json.loads(request.read())
    subject = body["file_id"] or body["alias"]
    return httpx2.Response(201, json=f"{body['work_type']}_wot_for_{subject}")


class WorkPackageApiMock(MockApi):
    """A mock of the Work Package API the connector calls, granting every token."""

    def __init__(self, base_url: str = WORK_PACKAGE_API_URL) -> None:
        super().__init__(base_url)
        self.on_get_work_package: ResponseHandler = respond(200, json={"files": {}})
        self.on_get_upload_wot: ResponseHandler = _upload_work_order_token
        self.on_get_download_wot: ResponseHandler = respond(201, json=WORK_ORDER_TOKEN)
        self.route("GET", WORK_PACKAGE_PATH, "on_get_work_package")
        self.route("POST", UPLOAD_WOT_PATH, "on_get_upload_wot")
        self.route("POST", DOWNLOAD_WOT_PATH, "on_get_download_wot")


# Download API paths, relative to `DOWNLOAD_API_URL`
DRS_OBJECT_PATH = "/objects/{file_id}"
ENVELOPE_PATH = f"{DRS_OBJECT_PATH}/envelopes"

# A plain staged DRS object, for tests that only need the Download API to answer
DRS_OBJECT: dict[str, Any] = {
    "access_methods": [{"access_url": {"url": "https://test.url"}, "type": "s3"}],
    "id": "test-file-id",
    "size": 1024,
}

# How long the presigned download URLs the mock hands out stay valid
URL_LIFESPAN = 10


@dataclass
class StagedObject:
    """An object the Download API reports as ready; its URL is presigned per request."""

    file_id: str
    size: int
    presign_download_url: Callable[[int], Awaitable[str]]
    envelope: bytes | None = None


def envelope_response(envelope: bytes) -> httpx2.Response:
    """Hand out `envelope` the way the Download API does, base64 encoded."""
    return httpx2.Response(200, content=base64.b64encode(envelope))


def no_such_drs_object(file_id: str) -> httpx2.Response:
    """Report the DRS object as unknown, as a plain `detail`, not httpyexpect."""
    return httpx2.Response(
        404, json={"detail": f'The DRSObject with the id "{file_id}" does not exist.'}
    )


def no_such_envelope(file_id: str) -> httpx2.Response:
    """Report the envelope as unknown, the way the envelope endpoint does."""
    return httpyexpect_error(
        404,
        "noSuchObject",
        f'The DRSObject with the id "{file_id}" does not exist.',
        {"file_id": file_id},
    )


class DownloadApiMock(MockApi):
    """A mock of the Download API the connector calls, serving the `staged` object."""

    def __init__(self, base_url: str = DOWNLOAD_API_URL) -> None:
        super().__init__(base_url)
        self.staged: StagedObject | None = None
        self.on_get_drs_object: ResponseHandler = self._describe_drs_object
        self.on_get_envelope: ResponseHandler = self._hand_out_envelope
        self.route("GET", ENVELOPE_PATH, "on_get_envelope")
        self.route("GET", DRS_OBJECT_PATH, "on_get_drs_object")

    async def _describe_drs_object(self, request: httpx2.Request) -> httpx2.Response:
        """Describe the object, or report it as unknown."""
        file_id = path_variables(request, DRS_OBJECT_PATH)["file_id"]
        staged = self.staged
        if staged is None or file_id != staged.file_id:
            return no_such_drs_object(file_id)

        download_url = await staged.presign_download_url(URL_LIFESPAN)
        now = now_as_utc().isoformat()
        return httpx2.Response(
            200,
            json={
                "file_id": staged.file_id,
                "self_uri": f"drs://localhost:8080//{staged.file_id}",
                "size": staged.size,
                "created_time": now,
                "updated_time": now,
                "checksums": [{"checksum": "1", "type": "md5"}],
                "access_methods": [{"access_url": {"url": download_url}, "type": "s3"}],
            },
        )

    def _hand_out_envelope(self, request: httpx2.Request) -> httpx2.Response:
        """Hand out the Crypt4GH envelope, for an object that has one."""
        file_id = path_variables(request, ENVELOPE_PATH)["file_id"]
        staged = self.staged
        if staged is None or file_id != staged.file_id or staged.envelope is None:
            return no_such_envelope(file_id)
        return envelope_response(staged.envelope)


class WkvsMock(MockApi):
    """A mock of the WKVS, pointing the connector at the other mocks."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self.on_get_values: ResponseHandler = respond(
            200,
            json={
                "crypt4gh_public_keys": TEST_PUBLIC_KEYS,
                "wps_api_url": WORK_PACKAGE_API_URL,
                "dcs_api_url": DOWNLOAD_API_URL,
                "ucs_api_url": UPLOAD_API_URL,
            },
        )
        self.route("GET", "/values", "on_get_values")


class StorageMock(MockApi):
    """Stands in for the object storage behind `UPLOAD_URL`, accepting every part."""

    def __init__(self, base_url: str = STORAGE_URL) -> None:
        super().__init__(base_url)
        self.on_upload_part: ResponseHandler = respond(200)
        self.route("PUT", "/part", "on_upload_part")


@dataclass
class MockApis:
    """The mocked GHGA APIs, and the storage behind their presigned URLs."""

    wkvs: WkvsMock
    work_package: WorkPackageApiMock
    download: DownloadApiMock
    upload: UploadApiMock
    storage: StorageMock


@pytest.fixture()
def mock_apis(monkeypatch) -> MockApis:
    """Serve every GHGA API from a mock, and refuse anything bound for the internet.

    The S3 testcontainer stays reachable; the rest is refused, since the default
    `wkvs_api_url` is a live GHGA URL.
    """
    # the test config's `client_num_retries=0` spares mocked 5xx answers a real backoff
    monkeypatch.setattr("ghga_connector.config.CONFIG", get_test_config())

    mocks = MockApis(
        wkvs=WkvsMock(get_test_config().wkvs_api_url),
        work_package=WorkPackageApiMock(),
        download=DownloadApiMock(),
        upload=UploadApiMock(),
        storage=StorageMock(),
    )
    served = serve(
        mocks.wkvs, mocks.work_package, mocks.download, mocks.upload, mocks.storage
    )

    def mock_mounts(config, limits=None):
        """Stand in for `ratelimiting_retry_proxies`."""
        return {"all://": MockApiTransport(served, MOCKED_BASE_URLS, limits=limits)}

    monkeypatch.setattr(
        "ghga_connector.core.client.ratelimiting_retry_proxies", mock_mounts
    )
    return mocks
