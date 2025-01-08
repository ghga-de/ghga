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


class UploadStatus(str, Enum):
    """Enum for the possible UploadStatus of a specific upload_id"""

    ACCEPTED = "accepted"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PENDING = "pending"
    REJECTED = "rejected"
    UPLOADED = "uploaded"


class StatePatch(BaseModel):
    """Model containing a state parameter. Needed for the UCS patch: /uploads/... api call"""

    status: UploadStatus


class StatePost(BaseModel):
    """Model containing a state parameter. Needed for the UCS post: /uploads api call"""

    file_id: str


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
    """The Upload Properties returned by the UCS post /uploads endpoint"""

    upload_id: str
    file_id: str
    part_size: int


class FileProperties(BaseModel):
    """The File Properties returned by the UCS get /files/{file_id} endpoint"""

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


@mock_external_app.get("/objects/{file_id}")
async def drs3_objects(file_id: str, request: Request, expires_after: UrlLifespan):
    """Mock for the drs3 /objects/{file_id} call.

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


@mock_external_app.get("/objects/{file_id}/envelopes")
async def drs3_objects_envelopes(file_id: str):
    """Mock for the dcs /objects/{file_id}/envelopes call"""
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


@mock_external_app.get("/files/{file_id}")
async def ulc_get_files(file_id: str):
    """Mock for the ulc GET /files/{file_id} call."""
    if file_id == "pending":
        return FileProperties(
            file_id=file_id,
            file_name=file_id,
            md5_checksum="",
            size=0,
            grouping_label="inbox",
            creation_date=now_as_utc(),
            update_date=now_as_utc(),
            format="",
            current_upload_id="pending",
        )

    raise HttpException(
        status_code=404,
        exception_id="fileNotRegistered",
        description=f'The file with the file_id "{file_id}" does not exist.',
        data={"file_id": file_id},
    )


@mock_external_app.get("/uploads/{upload_id}")
async def ulc_get_uploads(upload_id: str):
    """Mock for the ulc GET /uploads/{upload_id} call."""
    if upload_id == "pending":
        return Response(
            status_code=200,
            content=UploadProperties(
                upload_id="pending",
                file_id="pending",
                part_size=int(os.environ["DEFAULT_PART_SIZE"]),
            ).json(),
        )

    raise HttpException(
        status_code=404,
        exception_id="noSuchUpload",
        description=f'The upload with the id "{upload_id}" does not exist.',
        data={"upload_id": upload_id},
    )


@mock_external_app.post("/uploads")
async def ulc_post_files_uploads(request: Request):
    """Mock for the ulc POST /uploads call."""
    content = json.loads(await request.body())
    state: StatePost = StatePost(**content)

    file_id = state.file_id

    if file_id == "uploadable":
        return Response(
            status_code=200,
            content=UploadProperties(
                upload_id="pending",
                file_id=file_id,
                part_size=int(os.environ["DEFAULT_PART_SIZE"]),
            ).model_dump_json(),
        )
    if file_id == "uploadable-16":
        return Response(
            status_code=200,
            content=UploadProperties(
                upload_id="pending",
                file_id=file_id,
                part_size=16 * 1024 * 1024,
            ).model_dump_json(),
        )

    if file_id == "uploadable-8":
        return Response(
            status_code=200,
            content=UploadProperties(
                upload_id="pending",
                file_id=file_id,
                part_size=8 * 1024 * 1024,
            ).model_dump_json(),
        )
    if file_id == "pending":
        raise HttpException(
            status_code=403,
            exception_id="noFileAccess",
            description=f'Can`t start multipart upload for file with file id "{file_id}".',
            data={"file_id": file_id},
        )

    raise HttpException(
        status_code=400,
        exception_id="fileNotRegistered",
        description=f'The file with the file_id "{file_id}" does not exist.',
        data={"file_id": file_id},
    )


@mock_external_app.post("/uploads/{upload_id}/parts/{part_no}/signed_urls")
async def ulc_post_uploads_parts_files_signed_posts(upload_id: str, part_no: int):
    """Mock for the ulc POST /uploads/{upload_id}/parts/{part_no}/signed_urls call."""
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


@mock_external_app.patch("/uploads/{upload_id}")
async def ulc_patch_uploads(upload_id: str, request: Request):
    """Mock for the ulc PATCH /uploads/{upload_id} call"""
    content = json.loads(await request.body())
    state: StatePatch = StatePatch(**content)
    upload_status = state.status

    if upload_id == "uploaded":
        if upload_status == UploadStatus.CANCELLED:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        raise HttpException(
            status_code=400,
            exception_id="uploadNotPending",
            description=f'The upload with id "{upload_id}" can`t be set to "{upload_status}"',
            data={"upload_id": upload_id, "current_upload_status": upload_id},
        )

    if upload_id == "pending":
        if upload_status == UploadStatus.UPLOADED:
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        raise HttpException(
            status_code=400,
            exception_id="uploadStatusChange",
            description=f'The upload with id "{upload_id}" can`t be set to "{upload_status}"',
            data={"upload_id": upload_id, "target_status": upload_status},
        )

    if upload_id == "uploadable":
        raise HttpException(
            status_code=400,
            exception_id="uploadNotPending",
            description=f'The upload with id "{upload_id}" can`t be set to "{upload_status}"',
            data={"upload_id": upload_id, "current_upload_status": upload_id},
        )

    raise HttpException(
        status_code=404,
        exception_id="noSuchUpload",
        description=f'The upload with id "{upload_id}" does not exist',
        data={"upload_id": upload_id},
    )


@mock_external_app.post("/work-packages/{package_id}/files/{file_id}/work-order-tokens")
async def create_work_order_token(package_id: str, file_id: str):
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


@mock_external_app.get("/values/{value_name}")
async def mock_wkvs(value_name: str):
    """Mock the WKVS /values/value_name endpoint"""
    api_url = "http://127.0.0.1"
    values: dict[str, str] = {
        "crypt4gh_public_key": "qx5g31H7rdsq7sgkew9ElkLIXvBje4RxDVcAHcJD8XY=",
        "wps_api_url": api_url,
        "dcs_api_url": api_url,
        "ucs_api_url": api_url,
    }

    if value_name not in values:
        raise HttpException(
            status_code=404,
            exception_id="valueNotConfigured",
            description=f"The value {value_name} is not configured.",
            data={"value_name": value_name},
        )

    return JSONResponse(status_code=200, content={value_name: values[value_name]})


config = ApiConfigBase()
configure_app(mock_external_app, config)


def get_test_mounts():
    """Test-only version of `async_client` to route traffic to the specified app.

    Lets other traffic go out as usual, e.g. to the S3 testcontainer, while still using
    the same caching logic as the real client.
    """
    mock_app_transport = get_cache_transport(httpx.ASGITransport(app=mock_external_app))
    mounts = {
        "all://127.0.0.1": mock_app_transport,  # route traffic to the mock app
        "all://host.docker.internal": get_cache_transport(),  # let S3 traffic go out
    }
    return mounts


@pytest.fixture(scope="function")
def mock_external_calls(monkeypatch):
    """Monkeypatch the async_client so it only intercepts calls to the mock app"""
    monkeypatch.setattr("ghga_connector.core.client.get_mounts", get_test_mounts)
