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

"""Mocks of the APIs the connector calls, built on the service commons `ApiMock`.

Every API is modeled once, by an `ApiMock` declaring all of its endpoints. An endpoint
answers with whatever handler is currently assigned to the matching `on_...` attribute,
so a test only states how the endpoints it cares about behave and inherits a successful
response for the rest:
```
upload_api.on_delete_file = respond(404, json={"exception_id": "fileUploadNotFound"})
```
Handlers come from `respond`, or are any callable taking the request plus the endpoint's
path variables as keyword arguments. They may be `async`, which is what lets an
integration test answer out of the S3 testcontainer. Everything reaching a mock is
recorded in its `requests`, so assertions about what the connector sent belong after the
call under test, not inside a handler where a failure would surface as a request error.

Each mock answers only the requests addressed to its own base URL, and the `mock_apis`
fixture at the bottom mounts all of them behind one transport. That fixture is what
every test uses: a unit test reaches for the one mock it cares about, an integration
test lets the connector bootstrap itself from the WKVS mock and walk the rest.
"""

import base64
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx2
import pytest

from ghga_service_commons.api.mock_api import (
    ApiMock,
    endpoint,
    httpyexpect_body,
    httpyexpect_error_handler,
    respond,
)
from ghga_service_commons.api.mock_router import HttpException, MockRouter
from ghga_service_commons.utils.utc_dates import now_as_utc
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.router import MOCK_API_HOST, MockApiTransport
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
    "error_answering_router",
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


def error_answering_router() -> MockRouter[HttpException]:
    """Build the router a mocked API answers from.

    `MockRouter` signals a request that no endpoint matches by raising, which would come
    out of the transport as an exception rather than as a response. Turning it into the
    404 in the httpyexpect schema instead is what lets the connector's own error
    handling see an unmocked call the way it sees any other error from a real API.
    """
    return MockRouter(
        exception_handler=httpyexpect_error_handler,
        exceptions_to_handle=(HttpException,),
    )


# The paths the Upload API serves, relative to the Upload API URL
UPLOADS_PATH = "/boxes/{box_id}/uploads"
UPLOAD_PATH = f"{UPLOADS_PATH}/{{file_id}}"
PART_PATH = f"{UPLOAD_PATH}/parts/{{part_no}}"
# The presigned URL the Upload API hands out for a part by default
UPLOAD_URL = f"{STORAGE_URL}/part"
EMPTY_LISTING: dict[str, Any] = {"items": [], "total_count": 0}


def _created_file_upload(
    request: httpx2.Request, **path_variables: str
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


class UploadApiMock(ApiMock):
    """A mock of the Upload API endpoints the connector calls.

    By default every endpoint reports success: an upload is created for `TEST_FILE_ID`,
    the box lists no uploads, `UPLOAD_URL` is handed out for every part, and completing
    or deleting an upload succeeds.
    """

    on_create_file_upload = endpoint("POST", UPLOADS_PATH, _created_file_upload)
    on_get_box_uploads = endpoint("GET", UPLOADS_PATH, respond(200, json=EMPTY_LISTING))
    on_get_part_upload_url = endpoint("GET", PART_PATH, respond(200, json=UPLOAD_URL))
    on_complete_file_upload = endpoint("PATCH", UPLOAD_PATH, respond(204))
    on_delete_file = endpoint("DELETE", UPLOAD_PATH, respond(204))

    def __init__(self, base_url: str = UPLOAD_API_URL) -> None:
        """Serve the Upload API at `base_url`."""
        super().__init__(base_url=base_url, router=error_answering_router())


# The paths the Work Package API serves, relative to the Work Package API URL
WORK_PACKAGE_PATH = "/work-packages/{package_id}"
UPLOAD_WOT_PATH = f"{WORK_PACKAGE_PATH}/boxes/{{box_id}}/work-order-tokens"
DOWNLOAD_WOT_PATH = f"{WORK_PACKAGE_PATH}/files/{{file_id}}/work-order-tokens"

# Stands in for the encrypted token the WPS hands out. Tests patch `_decrypt` to the
# identity, so this is also what travels as the bearer token.
WORK_ORDER_TOKEN = base64.b64encode(b"1234567890" * 5).decode()


def _upload_work_order_token(
    request: httpx2.Request, **path_variables: str
) -> httpx2.Response:
    """Hand out a work order token naming what it authorizes.

    Since `_decrypt` is patched to the identity, this string is what travels as the
    bearer token - so it says what was asked for rather than being opaque.
    """
    body = json.loads(request.read())
    subject = body["file_id"] or body["alias"]
    return httpx2.Response(201, json=f"{body['work_type']}_wot_for_{subject}")


class WorkPackageApiMock(ApiMock):
    """A mock of the Work Package API endpoints the connector calls.

    By default the work package contains no files, and every work order token request is
    granted - a download token as the opaque `WORK_ORDER_TOKEN`, an upload token as a
    string naming the work it authorizes.
    """

    on_get_work_package = endpoint(
        "GET", WORK_PACKAGE_PATH, respond(200, json={"files": {}})
    )
    on_get_upload_wot = endpoint("POST", UPLOAD_WOT_PATH, _upload_work_order_token)
    on_get_download_wot = endpoint(
        "POST", DOWNLOAD_WOT_PATH, respond(201, json=WORK_ORDER_TOKEN)
    )

    def __init__(self, base_url: str = WORK_PACKAGE_API_URL) -> None:
        """Serve the Work Package API at `base_url`."""
        super().__init__(base_url=base_url, router=error_answering_router())


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
    request: httpx2.Request, file_id: str, **path_variables: str
) -> httpx2.Response:
    """Report the envelope as unknown, the way the envelope endpoint does."""
    return httpx2.Response(
        404,
        json=httpyexpect_body(
            "noSuchObject",
            f'The DRSObject with the id "{file_id}" does not exist.',
            {"file_id": file_id},
        ),
    )


class DownloadApiMock(ApiMock):
    """A mock of the Download API endpoints the connector calls.

    Nothing is staged to begin with, so every file is reported as unknown; assign
    `staged` to have one described as ready for download. Tests that want a refusal or a
    still-being-staged answer swap `on_get_drs_object` for a handler of their own.
    """

    on_get_envelope = endpoint("GET", ENVELOPE_PATH)
    on_get_drs_object = endpoint("GET", DRS_OBJECT_PATH)

    def __init__(self, base_url: str = DOWNLOAD_API_URL) -> None:
        """Serve the Download API at `base_url`."""
        super().__init__(base_url=base_url, router=error_answering_router())
        self.staged: StagedObject | None = None
        # the defaults answer out of `staged`, so they have to be bound per instance
        self.on_get_envelope = self._hand_out_envelope
        self.on_get_drs_object = self._describe_drs_object

    async def _describe_drs_object(
        self, request: httpx2.Request, file_id: str, **path_variables: str
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
        self, request: httpx2.Request, file_id: str, **path_variables: str
    ) -> httpx2.Response:
        """Hand out the Crypt4GH envelope, for an object that has one."""
        staged = self.staged
        if staged is None or file_id != staged.file_id or staged.envelope is None:
            return no_such_envelope(request, file_id)
        return envelope_response(staged.envelope)


class WkvsMock(ApiMock):
    """A mock of the well-known-value-service the connector bootstraps itself from.

    By default it points the connector at the other mocks in this module.
    """

    on_get_values = endpoint(
        "GET",
        "/values",
        respond(
            200,
            json={
                "crypt4gh_public_keys": TEST_PUBLIC_KEYS,
                "wps_api_url": WORK_PACKAGE_API_URL,
                "dcs_api_url": DOWNLOAD_API_URL,
                "ucs_api_url": UPLOAD_API_URL,
            },
        ),
    )

    def __init__(self, base_url: str) -> None:
        """Serve the WKVS at `base_url`."""
        super().__init__(base_url=base_url, router=error_answering_router())


@dataclass
class MockApis:
    """Every API the connector calls, mocked.

    Everything a test needs to arrange is a handler swap on one of these; `storage`
    stands in for the object storage the presigned URLs point at, and carries the
    one-off endpoints of a single test, registered with `add(...)`.
    """

    wkvs: WkvsMock
    work_package: WorkPackageApiMock
    download: DownloadApiMock
    upload: UploadApiMock
    storage: ApiMock

    @property
    def all(self) -> tuple[ApiMock, ...]:
        """Every mock, in the order a request is offered to them."""
        return (self.wkvs, self.work_package, self.download, self.upload, self.storage)

    @property
    def base_urls(self) -> tuple[str, ...]:
        """The base URLs the mocks answer for, and hence what counts as mocked.

        Taken off the mocks rather than listed beside them, so an API moving to another
        address cannot quietly start escaping to the network.
        """
        return tuple(mock.base_url for mock in self.all)


@pytest.fixture()
def mock_apis(monkeypatch) -> MockApis:
    """Serve every GHGA API from a mock, and refuse anything bound for the internet.

    Unit and integration tests share this one fixture: a unit test reaches for the single
    mock it cares about (`mock_apis.upload`), an integration test lets the connector
    bootstrap itself from `mock_apis.wkvs` and walk the rest. Traffic to the S3
    testcontainer still goes out, which is what makes the presigned URLs worth handing
    out; anything else is refused, since the connector's default `wkvs_api_url` is a live
    GHGA URL that a misconfigured test would otherwise call for real.

    A request that reaches a mock but matches none of its endpoints is answered with a
    404 rather than raising, so the connector sees an error response from an unmocked
    call just as it did from the FastAPI mock app.
    """
    # Mocked responses pass through the real retry transport, so without the test
    # config's `client_num_retries=0` every mocked 5xx would cost a real backoff sleep.
    monkeypatch.setattr("ghga_connector.config.CONFIG", get_test_config())

    mocks = MockApis(
        wkvs=WkvsMock(get_test_config().wkvs_api_url),
        work_package=WorkPackageApiMock(),
        download=DownloadApiMock(),
        upload=UploadApiMock(),
        storage=ApiMock(base_url=STORAGE_URL, router=error_answering_router()),
    )

    def mock_mounts(config, limits=None):
        """Stand in for `ratelimiting_retry_proxies`, sorting out where calls may go."""
        return {"all://": MockApiTransport(mocks.all, limits=limits)}

    monkeypatch.setattr(
        "ghga_connector.core.client.ratelimiting_retry_proxies", mock_mounts
    )
    return mocks
