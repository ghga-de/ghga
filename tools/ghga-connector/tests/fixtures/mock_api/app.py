# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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
All mocks work correclty with file_id == "1".
The drs3 mock sends back a "wait 1 minute" for file_id == "1m"
All other file_ids will fail
"""

import os
from datetime import datetime, timezone
from enum import Enum
from typing import List, Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

DEFAULT_PART_SIZE = 16 * 1024 * 1024


class UploadStatus(str, Enum):
    """
    Enum for the possible UploadStatus of a specific upload_id
    """

    ACCEPTED = "accepted"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PENDING = "pending"
    REJECTED = "rejected"
    UPLOADED = "uploaded"


class StatePatch(BaseModel):
    """
    Model containing a state parameter. Needed for the ULC get api call
    """

    upload_status: UploadStatus


class PresignedPostURL(BaseModel):
    """
    Model containing an url
    """

    url: str


class Checksum(BaseModel):
    """
    A Checksum as per the DRS OpenApi specs.
    """

    checksum: str
    type: Literal["md5", "sha-256"]


class AccessURL(BaseModel):
    """Describes the URL for accessing the actual bytes of the object as per the
    DRS OpenApi spec."""

    url: str


class AccessMethod(BaseModel):
    """An AccessMethod as per the DRS OpenApi spec."""

    access_url: AccessURL
    type: Literal["s3"] = "s3"  # currently only s3 is supported


class UploadProperties(BaseModel):
    """A AccessMethod as per the DRS OpenApi spec."""

    upload_id: str
    part_size: int


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
    checksums: List[Checksum]
    access_methods: List[AccessMethod]


app = FastAPI()


@app.get("/ready", summary="readyness_probe")
async def ready():
    """
    Readyness probe.
    """
    return JSONResponse(None, status_code=status.HTTP_204_NO_CONTENT)


@app.get("/objects/{file_id}", summary="drs3_mock")
async def drs3_objects(file_id: str):

    """
    Mock for the drs3 /objects/{file_id} call
    """

    if file_id == "retry":
        return Response(
            status_code=status.HTTP_202_ACCEPTED, headers={"Retry-After": "10"}
        )

    if file_id == "downloadable" or file_id == "big-downloadable":

        return DrsObjectServe(
            file_id=file_id,
            self_uri=f"drs://localhost:8080//{file_id}",
            size=int(os.environ["S3_DOWNLOAD_FIELD_SIZE"]),
            created_time=datetime.now(timezone.utc).isoformat(),
            updated_time=datetime.now(timezone.utc).isoformat(),
            checksums=[Checksum(checksum="1", type="md5")],
            access_methods=[
                AccessMethod(
                    access_url=AccessURL(url=os.environ["S3_DOWNLOAD_URL"]), type="s3"
                )
            ],
        )

    raise HTTPException(
        status_code=404,
        detail=(f'The DRSObject with the id "{file_id}" does not exist.'),
    )


@app.get(
    "/files/{file_id}/uploads", summary="ulc_get_files_uploads_mock", status_code=200
)
async def ulc_get_files_uploads(file_id: str, upload_status: str):

    """
    Mock for the ulc GET /files/{file_id}/uploads call.
    """
    if upload_status == UploadStatus.PENDING:

        if file_id == "pending":
            return [
                UploadProperties(
                    upload_id="pending",
                    part_size=DEFAULT_PART_SIZE,
                )
            ]

        if file_id == "uploaded":
            return []

    raise HTTPException(
        status_code=404,
        detail=(f'The file with the file_id "{file_id}" does not exist.'),
    )


@app.post(
    "/files/{file_id}/uploads", summary="ulc_post_files_uploads_mock", status_code=200
)
async def ulc_post_files_uploads(file_id: str):
    """
    Mock for the ulc POST /files/{file_id}/uploads call.
    """

    if file_id == "uploadable":
        return UploadProperties(
            upload_id="pending",
            part_size=DEFAULT_PART_SIZE,
        )
    if file_id == "uploadable-16":
        return UploadProperties(
            upload_id="pending",
            part_size=16 * 1024 * 1024,
        )

    if file_id == "uploadable-5":
        return UploadProperties(
            upload_id="pending",
            part_size=5 * 1024 * 1024,
        )
    if file_id == "pending":
        raise HTTPException(
            status_code=403,
            detail=(f'Can`t start multipart upload for file with file id "{file_id}".'),
        )

    raise HTTPException(
        status_code=404,
        detail=(f'The file with the file_id "{file_id}" does not exist.'),
    )


@app.post(
    "/uploads/{upload_id}/parts/{part_no}/signed_posts",
    summary="ulc_post_uploads_parts_files_signed_posts_mock",
    status_code=200,
)
async def ulc_post_uploads_parts_files_signed_posts(upload_id: str, part_no: int):
    """
    Mock for the ulc POST /uploads/{upload_id}/parts/{part_no}/signed_posts call.
    """

    if upload_id == "pending":
        if part_no == 1:
            url = os.environ["S3_UPLOAD_URL_1"]
            return {"presigned_post": url}
        if part_no == 2:
            url = os.environ["S3_UPLOAD_URL_2"]
            return {"presigned_post": url}

    raise HTTPException(
        status_code=404,
        detail=(f'The file with the upload id "{upload_id}" does not exist.'),
    )


@app.patch("/uploads/{upload_id}", summary="ulc_patch_uploads_mock", status_code=204)
async def ulc_patch_uploads(upload_id: str, state: StatePatch):

    """
    Mock for the ulc PATCH /uploads/{upload_id} call
    """
    upload_status = state.upload_status

    if upload_id == "uploaded":
        if upload_status == UploadStatus.CANCELLED:
            return JSONResponse(None, status_code=status.HTTP_204_NO_CONTENT)

        raise HTTPException(
            status_code=403,
            detail=(
                f'The upload with id "{upload_id}" can`t be set to "{upload_status}"'
            ),
        )

    if upload_id == "pending":
        if upload_status == UploadStatus.UPLOADED:
            return JSONResponse(None, status_code=status.HTTP_204_NO_CONTENT)

        raise HTTPException(
            status_code=403,
            detail=(
                f'The upload with id "{upload_id}" can`t be set to "{upload_status}"'
            ),
        )

    raise HTTPException(
        status_code=404,
        detail=(f'The upload with id "{upload_id}" does not exist'),
    )
