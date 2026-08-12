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

"""Mocks of the APIs the connector calls, served from a `MockRouter`.

Every API is modeled once, by a class registering all of its endpoints on the router it
is handed. An endpoint answers with whatever handler is currently assigned to the
matching `on_...` attribute, so a test only states how the endpoints it cares about
behave and inherits a successful response for the rest:
```
upload_api.on_delete_file = respond(404, json={"exception_id": "fileUploadNotFound"})
```
Handlers come from `respond`, or are any callable taking the request plus the endpoint's
path variables as keyword arguments. They may be `async`, which is what lets an
integration test answer out of the S3 testcontainer. Everything reaching a mock is
recorded in its `requests`, so assertions about what the connector sent belong after the
call under test, not inside a handler where a failure would surface as a request error.

The `mock_apis` fixture at the bottom serves all of them at once, and is what every test
uses: a unit test reaches for the one mock it cares about, an integration test lets the
connector bootstrap itself from the WKVS mock and walk the rest.
"""

import base64
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx2
import pytest

from ghga_service_commons.api.mock_router import HttpException, MockRouter
from ghga_service_commons.utils.utc_dates import now_as_utc
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.router import (
    MOCK_API_HOST,
    MockApiTransport,
    ResponseHandler,
    api_url,
    httpyexpect_error,
    httpyexpect_response,
    respond,
)
from tests.fixtures.utils import TEST_FILE_ID, TEST_PUBLIC_KEYS, TEST_STORAGE_ALIAS1

__all__ = [
    "DOWNLOAD_API_URL",
    "DRS_OBJECT",
    "UPLOAD_API_URL",
    "UPLOAD_URL",
    "WORK_ORDER_TOKEN",
    "WORK_PACKAGE_API_URL",
    "DownloadApiMock",
    "MockApis",
    "StagedObject",
    "UploadApiMock",
    "WkvsMock",
    "WorkPackageApiMock",
    "mock_apis",
]

# Where the mocked APIs live. `set_runtime_test_config` points the connector's own
# config at these same URLs, and the WKVS mock announces them, so a unit test and an
# integration test reach the same mocks by the same addresses.
UPLOAD_API_URL = f"http://{MOCK_API_HOST}/upload"
DOWNLOAD_API_URL = f"http://{MOCK_API_HOST}/download"
WORK_PACKAGE_API_URL = f"http://{MOCK_API_HOST}/work"
# Stands in for object storage, which in integration tests is the S3 testcontainer at a
# real address. Presigned URLs the mocks hand out live under here.
STORAGE_URL = f"http://{MOCK_API_HOST}/storage"

# Everything the mocks answer for. A request under one of these is served by the router;
# anything else either belongs to the test environment or is refused outright.
MOCKED_BASE_URLS = (
    get_test_config().wkvs_api_url,
    UPLOAD_API_URL,
    DOWNLOAD_API_URL,
    WORK_PACKAGE_API_URL,
    STORAGE_URL,
)


class _ApiMock:
    """Shared behavior of the API mocks: recording requests and dispatching handlers."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []

    @property
    def last_request(self) -> httpx2.Request:
        """The most recent request that reached this mock."""
        assert self.requests, f"No request reached the {type(self).__name__}"
        return self.requests[-1]

    async def _handle(
        self, request: httpx2.Request, handler: ResponseHandler, **path_variables: Any
    ) -> httpx2.Response:
        """Record the request and let the currently assigned handler answer it."""
        self.requests.append(request)
        answer = handler(request, **path_variables)
        return answer if isinstance(answer, httpx2.Response) else await answer


# The paths the Upload API serves, relative to the Upload API URL
UPLOADS_PATH = "/boxes/{box_id}/uploads"
UPLOAD_PATH = f"{UPLOADS_PATH}/{{file_id}}"
PART_PATH = f"{UPLOAD_PATH}/parts/{{part_no}}"
# The presigned URL the Upload API hands out for a part by default
UPLOAD_URL = f"{STORAGE_URL}/part"
EMPTY_LISTING: dict[str, Any] = {"items": [], "total_count": 0}


def _created_file_upload(
    request: httpx2.Request, **path_variables: Any
) -> httpx2.Response:
    """Report the file upload as created, echoing back the requested alias.

    The connector rejects a response for an alias other than the one it asked for, so
    this cannot be a canned `respond(...)` body.
    """
    return httpx2.Response(
        201,
        json={
            "file_id": str(TEST_FILE_ID),
            "alias": json.loads(request.read())["alias"],
            "storage_alias": TEST_STORAGE_ALIAS1,
        },
    )


class UploadApiMock(_ApiMock):
    """A mock of the Upload API endpoints the connector calls.

    By default every endpoint reports success: an upload is created for `TEST_FILE_ID`,
    the box lists no uploads, `UPLOAD_URL` is handed out for every part, and completing
    or deleting an upload succeeds.
    """

    def __init__(self, router: MockRouter, base_url: str = UPLOAD_API_URL) -> None:
        super().__init__()
        self.on_create_file_upload: ResponseHandler = _created_file_upload
        self.on_get_box_uploads: ResponseHandler = respond(200, json=EMPTY_LISTING)
        self.on_get_part_upload_url: ResponseHandler = respond(200, json=UPLOAD_URL)
        self.on_complete_file_upload: ResponseHandler = respond(204)
        self.on_delete_file: ResponseHandler = respond(204)

        @router.post(api_url(base_url, UPLOADS_PATH))
        async def create_file_upload(
            box_id: UUID, request: httpx2.Request
        ) -> httpx2.Response:
            """Create a new file upload in the box."""
            return await self._handle(
                request, self.on_create_file_upload, box_id=box_id
            )

        @router.get(api_url(base_url, UPLOADS_PATH))
        async def get_box_uploads(
            box_id: UUID, request: httpx2.Request
        ) -> httpx2.Response:
            """List the uploads the box contains."""
            return await self._handle(request, self.on_get_box_uploads, box_id=box_id)

        @router.get(api_url(base_url, PART_PATH))
        async def get_part_upload_url(
            box_id: UUID, file_id: UUID, part_no: int, request: httpx2.Request
        ) -> httpx2.Response:
            """Hand out the presigned upload URL for a part."""
            return await self._handle(
                request,
                self.on_get_part_upload_url,
                box_id=box_id,
                file_id=file_id,
                part_no=part_no,
            )

        @router.patch(api_url(base_url, UPLOAD_PATH))
        async def complete_file_upload(
            box_id: UUID, file_id: UUID, request: httpx2.Request
        ) -> httpx2.Response:
            """Complete the file upload."""
            return await self._handle(
                request, self.on_complete_file_upload, box_id=box_id, file_id=file_id
            )

        @router.delete(api_url(base_url, UPLOAD_PATH))
        async def delete_file(
            box_id: UUID, file_id: UUID, request: httpx2.Request
        ) -> httpx2.Response:
            """Delete the file upload."""
            return await self._handle(
                request, self.on_delete_file, box_id=box_id, file_id=file_id
            )


# The paths the Work Package API serves, relative to the Work Package API URL
WORK_PACKAGE_PATH = "/work-packages/{package_id}"
UPLOAD_WOT_PATH = f"{WORK_PACKAGE_PATH}/boxes/{{box_id}}/work-order-tokens"
DOWNLOAD_WOT_PATH = f"{WORK_PACKAGE_PATH}/files/{{file_id}}/work-order-tokens"

# Stands in for the encrypted token the WPS hands out. Tests patch `_decrypt` to the
# identity, so this is also what travels as the bearer token.
WORK_ORDER_TOKEN = base64.b64encode(b"1234567890" * 5).decode()


def _upload_work_order_token(
    request: httpx2.Request, **path_variables: Any
) -> httpx2.Response:
    """Hand out a work order token naming what it authorizes.

    Since `_decrypt` is patched to the identity, this string is what travels as the
    bearer token - so it says what was asked for rather than being opaque.
    """
    body = json.loads(request.read())
    subject = body["file_id"] or body["alias"]
    return httpx2.Response(201, json=f"{body['work_type']}_wot_for_{subject}")


class WorkPackageApiMock(_ApiMock):
    """A mock of the Work Package API endpoints the connector calls.

    By default the work package contains no files, and every work order token request is
    granted - a download token as the opaque `WORK_ORDER_TOKEN`, an upload token as a
    string naming the work it authorizes.
    """

    def __init__(
        self, router: MockRouter, base_url: str = WORK_PACKAGE_API_URL
    ) -> None:
        super().__init__()
        self.on_get_work_package: ResponseHandler = respond(200, json={"files": {}})
        self.on_get_upload_wot: ResponseHandler = _upload_work_order_token
        self.on_get_download_wot: ResponseHandler = respond(201, json=WORK_ORDER_TOKEN)

        @router.get(api_url(base_url, WORK_PACKAGE_PATH))
        async def get_work_package(
            package_id: str, request: httpx2.Request
        ) -> httpx2.Response:
            """Describe the work package, including the files it grants access to."""
            return await self._handle(
                request, self.on_get_work_package, package_id=package_id
            )

        @router.post(api_url(base_url, UPLOAD_WOT_PATH))
        async def get_upload_wot(
            package_id: UUID, box_id: UUID, request: httpx2.Request
        ) -> httpx2.Response:
            """Hand out a work order token for an upload box."""
            return await self._handle(
                request, self.on_get_upload_wot, package_id=package_id, box_id=box_id
            )

        @router.post(api_url(base_url, DOWNLOAD_WOT_PATH))
        async def get_download_wot(
            package_id: str, file_id: str, request: httpx2.Request
        ) -> httpx2.Response:
            """Hand out a work order token for a file download."""
            return await self._handle(
                request,
                self.on_get_download_wot,
                package_id=package_id,
                file_id=file_id,
            )


# The paths the Download API serves, relative to the Download API URL
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
    """An object the Download API reports as ready, and how to reach the bytes.

    `presign_download_url` is called for every request, so the URL it hands out can be
    short-lived without the object ever becoming unreachable - which is what makes the
    connector go and refresh an expired one.
    """

    file_id: str
    size: int
    presign_download_url: Callable[[int], Awaitable[str]]
    envelope: bytes | None = None


def envelope_response(envelope: bytes) -> httpx2.Response:
    """Hand out `envelope` the way the Download API does, base64 encoded."""
    return httpx2.Response(200, content=base64.b64encode(envelope))


def no_such_drs_object(file_id: str) -> httpx2.Response:
    """Report the DRS object as unknown, the way the object endpoint does.

    Unlike the rest of the Download API's errors, this one is not in the httpyexpect
    schema - it only carries a `detail`, and the connector copes with either.
    """
    return httpx2.Response(
        404, json={"detail": f'The DRSObject with the id "{file_id}" does not exist.'}
    )


def no_such_envelope(
    request: httpx2.Request, file_id: str, **path_variables: Any
) -> httpx2.Response:
    """Report the envelope as unknown, the way the envelope endpoint does."""
    return httpyexpect_error(
        404,
        "noSuchObject",
        f'The DRSObject with the id "{file_id}" does not exist.',
        {"file_id": file_id},
    )


class DownloadApiMock(_ApiMock):
    """A mock of the Download API endpoints the connector calls.

    Nothing is staged to begin with, so every file is reported as unknown; assign
    `staged` to have one described as ready for download. Tests that want a refusal or a
    still-being-staged answer swap `on_get_drs_object` for a handler of their own.
    """

    def __init__(self, router: MockRouter, base_url: str = DOWNLOAD_API_URL) -> None:
        super().__init__()
        self.staged: StagedObject | None = None
        self.on_get_drs_object: ResponseHandler = self._describe_drs_object
        self.on_get_envelope: ResponseHandler = self._hand_out_envelope

        @router.get(api_url(base_url, ENVELOPE_PATH))
        async def get_envelope(
            file_id: str, request: httpx2.Request
        ) -> httpx2.Response:
            """Hand out the Crypt4GH envelope of the file."""
            return await self._handle(request, self.on_get_envelope, file_id=file_id)

        @router.get(api_url(base_url, DRS_OBJECT_PATH))
        async def get_drs_object(
            file_id: str, request: httpx2.Request
        ) -> httpx2.Response:
            """Describe the DRS object, including where to download it from."""
            return await self._handle(request, self.on_get_drs_object, file_id=file_id)

    async def _describe_drs_object(
        self, request: httpx2.Request, file_id: str, **path_variables: Any
    ) -> httpx2.Response:
        """Describe the object, or report it as unknown."""
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

    def _hand_out_envelope(
        self, request: httpx2.Request, file_id: str, **path_variables: Any
    ) -> httpx2.Response:
        """Hand out the Crypt4GH envelope, for an object that has one."""
        staged = self.staged
        if staged is None or file_id != staged.file_id or staged.envelope is None:
            return no_such_envelope(request, file_id)
        return envelope_response(staged.envelope)


class WkvsMock(_ApiMock):
    """A mock of the well-known-value-service the connector bootstraps itself from.

    By default it points the connector at the other mocks in this module.
    """

    def __init__(self, router: MockRouter, base_url: str) -> None:
        super().__init__()
        self.on_get_values: ResponseHandler = respond(
            200,
            json={
                "crypt4gh_public_keys": TEST_PUBLIC_KEYS,
                "wps_api_url": WORK_PACKAGE_API_URL,
                "dcs_api_url": DOWNLOAD_API_URL,
                "ucs_api_url": UPLOAD_API_URL,
            },
        )

        @router.get(api_url(base_url, "/values"))
        async def get_values(request: httpx2.Request) -> httpx2.Response:
            """Announce the well-known values, the API URLs among them."""
            return await self._handle(request, self.on_get_values)


@dataclass
class MockApis:
    """The mocked GHGA APIs, and the router serving all of them.

    Everything a test needs to arrange is a handler swap on one of the mocks; `router` is
    there for the rare endpoint no GHGA API serves.
    """

    router: MockRouter
    wkvs: WkvsMock
    work_package: WorkPackageApiMock
    download: DownloadApiMock
    upload: UploadApiMock


@pytest.fixture()
def mock_apis(monkeypatch) -> MockApis:
    """Serve every GHGA API from a mock, and refuse anything bound for the internet.

    Unit and integration tests share this one fixture: a unit test reaches for the single
    mock it cares about (`mock_apis.upload`), an integration test lets the connector
    bootstrap itself from `mock_apis.wkvs` and walk the rest. Traffic to the S3
    testcontainer still goes out, which is what makes the presigned URLs worth handing
    out; anything else is refused, since the connector's default `wkvs_api_url` is a live
    GHGA URL that a misconfigured test would otherwise call for real.

    A request no endpoint matches is answered with the 404 the `MockRouter` raises for it
    rather than that exception surfacing out of the transport, so the connector sees an
    error response from an unmocked call just as it did from the FastAPI mock app.
    """
    # Mocked responses pass through the real retry transport, so without the test
    # config's `client_num_retries=0` every mocked 5xx would cost a real backoff sleep.
    monkeypatch.setattr("ghga_connector.config.CONFIG", get_test_config())

    router: MockRouter[HttpException] = MockRouter(
        exception_handler=httpyexpect_response,
        exceptions_to_handle=(HttpException,),
    )
    mocks = MockApis(
        router=router,
        wkvs=WkvsMock(router, get_test_config().wkvs_api_url),
        work_package=WorkPackageApiMock(router),
        download=DownloadApiMock(router),
        upload=UploadApiMock(router),
    )

    def mock_mounts(config, limits=None):
        """Stand in for `ratelimiting_retry_proxies`, sorting out where calls may go."""
        return {"all://": MockApiTransport(router, MOCKED_BASE_URLS, limits=limits)}

    monkeypatch.setattr(
        "ghga_connector.core.client.ratelimiting_retry_proxies", mock_mounts
    )
    return mocks
