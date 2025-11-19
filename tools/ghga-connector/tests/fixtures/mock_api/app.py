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

"""
Runs a small fastapi mock server for testing purposes.
All mocks work correctly with file_id == "1".
The drs3 mock sends back a "wait 1 minute" for file_id == "1m"
All other file_ids will fail
"""

import base64
import json
import os
from datetime import datetime
from email.utils import format_datetime
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from ghga_service_commons.api.api import ApiConfigBase, configure_app
from ghga_service_commons.api.di import DependencyDummy
from ghga_service_commons.httpyexpect.server.exceptions import HttpException
from ghga_service_commons.utils.utc_dates import now_as_utc
from pydantic import BaseModel

from ghga_connector.core.client import get_cache_transport

WORK = "/work"
UPLOAD = "/upload"
DOWNLOAD = "/download"
FILE_UPLOAD_ID1 = UUID("310282cc-1469-4ae4-8653-a6497bc972be")


class UploadStatus(str, Enum):
    """Enum for the possible UploadStatus of a specific upload_id"""

    ACCEPTED = "accepted"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PENDING = "pending"
    REJECTED = "rejected"
    UPLOADED = "uploaded"


class Checksum(BaseModel):
    """A Checksum as per the DRS OpenApi specs."""

    checksum: str
    type: Literal["md5", "sha-256"]


class AccessURL(BaseModel):
    """Describes the URL for accessing the actual bytes of the object as per the
    DRS OpenApi spec.
    """

    url: str


class AccessMethod(BaseModel):
    """An AccessMethod as per the DRS OpenApi spec."""

    access_url: AccessURL
    type: Literal["s3"] = "s3"  # currently only s3 is supported


class UploadProperties(BaseModel):
    """The Upload Properties returned by the Upload API post /uploads endpoint"""

    upload_id: str
    file_id: str
    part_size: int


class FileProperties(BaseModel):
    """The File Properties returned by the Upload API get /files/{file_id} endpoint"""

    file_id: str
    file_name: str
    md5_checksum: str
    size: int
    grouping_label: str
    creation_date: datetime
    update_date: datetime
    format: str
    current_upload_id: str


class DrsObjectServe(BaseModel):
    """
    A model containing a DrsObject as per the DRS OpenApi specs.
    This is used to serve metadata on a DrsObject (including the access methods) to the
    user.
    """

    file_id: str  # the file ID
    self_uri: str
    size: int
    created_time: str
    updated_time: str
    checksums: list[Checksum]
    access_methods: list[AccessMethod]


class HttpEnvelopeResponse(Response):
    """Return base64 encoded envelope bytes"""

    response_id = "envelope"

    def __init__(self, *, envelope: str, status_code: int = 200):
        """Construct message and init the response."""
        super().__init__(content=envelope, status_code=status_code)


def create_caching_headers(expires_after: int = 60) -> dict[str, str]:
    """Return headers used in responses for caching by `hishel`"""
    cache_control_header = ("Cache-Control", f"max-age={expires_after}, private")
    date_header = ("date", format_datetime(now_as_utc()))
    return {k: v for k, v in [cache_control_header, date_header]}


mock_external_app = FastAPI()
url_expires_after = DependencyDummy("url_expires_after")
UrlLifespan = Annotated[int, Depends(url_expires_after)]


async def update_presigned_url_placeholder():
    """Placeholder function to generate a new S3 download URL.

    Patch this function only via `set_presigned_url_update_endpoint`.

    This is stand-in logic for how the download controller creates a pre-signed
    S3 download URL when its `/objects/{file_id}` endpoint is called.
    """
    raise NotImplementedError()


@mock_external_app.get("/")
async def ready():
    """Readiness probe."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@mock_external_app.get("/health")
async def health():
    """Used to test if this service is alive"""
    return Response(
        status_code=status.HTTP_200_OK, content=json.dumps({"status": "OK"})
    )


@mock_external_app.get(DOWNLOAD + "/objects/{file_id}")
async def drs3_objects(file_id: str, request: Request, expires_after: UrlLifespan):
    """Mock for the Download API's /objects/{file_id} call.

    The `url_expires_after` parameter is an app dependency that is overridden by tests
    that use this mock api.
    """
    # get authorization header
    authorization = request.headers["authorization"]

    # simulate token authorization error
    if authorization == "Bearer authfail_normal":
        raise HTTPException(
            status_code=403,
            detail="This is not the token you're looking for.",
        )

    # simulate token file_id/object_id mismatch
    if authorization == "Bearer file_id_mismatch":
        raise HttpException(
            status_code=403,
            exception_id="wrongFileAuthorizationError",
            description="Endpoint file ID did not match file ID announced in work order token.",
            data={},
        )

    if file_id == "retry":
        return Response(
            status_code=status.HTTP_202_ACCEPTED,
            headers={"Retry-After": "10", "Cache-Control": "no-store"},
        )

    if file_id in ("downloadable", "big-downloadable", "envelope-missing"):
        await update_presigned_url_placeholder()
        return Response(
            status_code=200,
            headers=create_caching_headers(expires_after=expires_after),
            content=DrsObjectServe(
                file_id=file_id,
                self_uri=f"drs://localhost:8080//{file_id}",
                size=int(os.environ["S3_DOWNLOAD_FIELD_SIZE"]),
                created_time=now_as_utc().isoformat(),
                updated_time=now_as_utc().isoformat(),
                checksums=[Checksum(checksum="1", type="md5")],
                access_methods=[
                    AccessMethod(
                        access_url=AccessURL(url=os.environ["S3_DOWNLOAD_URL"]),
                        type="s3",
                    )
                ],
            ).model_dump_json(),
        )

    raise HTTPException(
        status_code=404,
        detail=f'The DRSObject with the id "{file_id}" does not exist.',
    )


@mock_external_app.get(DOWNLOAD + "/objects/{file_id}/envelopes")
async def drs3_objects_envelopes(file_id: str):
    """Mock for the Download API's /objects/{file_id}/envelopes call"""
    if file_id in ("downloadable", "big-downloadable"):
        response_str = str.encode(os.environ["FAKE_ENVELOPE"])
        envelope = base64.b64encode(response_str).decode("utf-8")
        response = HttpEnvelopeResponse(envelope=envelope)
        response.headers["Cache-Control"] = "no-store"
        return response

    raise HttpException(
        status_code=404,
        exception_id="noSuchObject",
        description=(f'The DRSObject with the id "{file_id}" does not exist.'),
        data={"file_id": file_id},
    )


@mock_external_app.post(UPLOAD + "/uploads/{upload_id}/parts/{part_no}/signed_urls")
async def post_uploads_parts_files_signed_posts(upload_id: str, part_no: int):
    """Mock for the Upload Api's POST /uploads/{upload_id}/parts/{part_no}/signed_urls call."""
    if upload_id == "pending":
        if part_no in (1, 2):
            urls = (os.environ["S3_UPLOAD_URL_1"], os.environ["S3_UPLOAD_URL_2"])
            return Response(
                status_code=200, content=json.dumps({"url": urls[part_no - 1]})
            )

    raise HttpException(
        status_code=404,
        exception_id="noSuchUpload",
        description=f'The file with the upload id "{upload_id}" does not exist.',
        data={"upload_id": upload_id},
    )


async def init_upload_placeholder(object_id: str):
    """This is a placeholder function for initiating an actual S3 multipart upload"""
    raise NotImplementedError()


@mock_external_app.post(UPLOAD + "/boxes/{box_id}/uploads")
async def create_file_upload(box_id: UUID, request: Request):
    """Mock for Upload API's POST /boxes/{box_id}/uploads endpoint.

    Due to test constraints, the upload is actually created ahead of time in the test
    fixture itself. This function returns a file ID.
    """
    _ = json.loads(await request.body())["alias"]
    file_id = str(uuid4())
    await init_upload_placeholder(object_id=file_id)
    return JSONResponse(status_code=201, content=file_id)


async def update_part_upload_url_placeholder(object_id: str, part_no: int) -> str:
    """Placeholder function to generate a new S3 upload URL."""
    raise NotImplementedError()


@mock_external_app.get(UPLOAD + "/boxes/{box_id}/uploads/{file_id}/parts/{part_no}")
async def get_upload_url(box_id: UUID, file_id: UUID, part_no: int, request: Request):
    """Returns a part upload URL for an in-progress multipart upload"""
    url = await update_part_upload_url_placeholder(str(file_id), part_no)
    return JSONResponse(status_code=200, content=url)


async def terminate_upload_placeholder(object_id: str):
    """Placeholder for a function that terminates an S3 multipart upload."""
    raise NotImplementedError()


@mock_external_app.patch(UPLOAD + "/boxes/{box_id}/uploads/{file_id}")
async def complete_file_upload(box_id: UUID, file_id: UUID, request: Request):
    """Mock for the Upload API's PATCH /boxes/{box_id}/uploads/{file_id} endpoint.

    This endpoint terminates the upload and verifies the checksum of the encrypted file.
    """
    await terminate_upload_placeholder(str(file_id))
    return Response(status_code=204)


@mock_external_app.post(
    WORK + "/work-packages/{package_id}/files/{file_id}/work-order-tokens"
)
async def get_download_wot(package_id: str, file_id: str):
    """Mock Work Order Token endpoint.

    Cached response will be valid for 5 seconds for testing purposes.
    Since client requests (should) use the min-fresh cache-control header value of 3
    seconds, the cached responses will be used for 2 seconds before making new requests.
    """
    # has to be at least 48 chars long
    headers = create_caching_headers(expires_after=5)
    return JSONResponse(
        status_code=201,
        content=base64.b64encode(b"1234567890" * 5).decode(),
        headers=headers,
    )


@mock_external_app.post(
    WORK + "/work-packages/{package_id}/boxes/{box_id}/work-order-tokens"
)
async def get_upload_wot(package_id: UUID, request: Request):
    """Mock Upload Work Order Token endpoint."""
    body = json.loads(await request.body())
    work_type = body["work_type"]
    file_id = body["file_id"]
    file_alias = body["alias"]
    headers = create_caching_headers(expires_after=5)
    return JSONResponse(
        status_code=201,
        content=f"{work_type}_wot_for_{file_id or file_alias}",
        headers=headers,
    )


@mock_external_app.get("/values")
async def mock_wkvs():
    """Mock the WKVS /values endpoint"""
    api_url = "http://127.0.0.1"
    values: dict[str, str] = {
        "crypt4gh_public_key": "qx5g31H7rdsq7sgkew9ElkLIXvBje4RxDVcAHcJD8XY=",
        "wps_api_url": f"{api_url}{WORK}",
        "dcs_api_url": f"{api_url}{DOWNLOAD}",
        "ucs_api_url": f"{api_url}{UPLOAD}",
    }

    return JSONResponse(status_code=200, content=values)


config = ApiConfigBase()
configure_app(mock_external_app, config)


def get_test_mounts(
    base_transport: httpx.AsyncHTTPTransport | None = None,
    limits: httpx.Limits | None = None,
):
    """Test-only version of `async_client` to route traffic to the specified app.

    Lets other traffic go out as usual, e.g. to the S3 testcontainer, while still using
    the same caching logic as the real client.
    """
    mock_app_transport = get_cache_transport(
        base_transport=httpx.ASGITransport(app=mock_external_app), limits=limits
    )
    mounts = {
        "all://127.0.0.1": mock_app_transport,  # route traffic to the mock app
        "all://host.docker.internal": get_cache_transport(
            base_transport=base_transport, limits=limits
        ),  # let S3 traffic go out
    }
    return mounts


@pytest.fixture(scope="function")
def mock_external_calls(monkeypatch):
    """Monkeypatch the async_client so it only intercepts calls to the mock app"""
    monkeypatch.setattr("ghga_connector.core.client.get_mounts", get_test_mounts)
