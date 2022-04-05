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


# fmt: off
class UploadState(Enum):

    """
    The current upload state. Can be registered (no information),
    pending (the user has requested an upload url),
    uploaded (the user has confirmed the upload),
    or registered (the file has been registered with the internal-file-registry).
    """

    REGISTERED = "registered"
    PENDING = "pending"
    UPLOADED = "uploaded"
    COMPLETED = "completed"
# fmt: on


class State(BaseModel):
    """
    Model containing a state parameter. Needed for the ULC confirm api call
    """

    state: UploadState


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
    """A AccessMethod as per the DRS OpenApi spec."""

    access_url: AccessURL
    type: Literal["s3"] = "s3"  # currently only s3 is supported


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
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/objects/{file_id}", summary="drs3_mock")
async def drs3_objects(file_id: str):

    """
    Mock for the drs3 /objects/{file_id} call
    """

    if file_id == "10s":
        return Response(
            status_code=status.HTTP_202_ACCEPTED, headers={"Retry-After": "10"}
        )

    if file_id == "1":

        download_url = os.environ["MOCK_DOWNLOAD_URL"]

        return DrsObjectServe(
            file_id=file_id,
            self_uri=f"drs://localhost:8080//{file_id}",
            size=1000,
            created_time=datetime.now(timezone.utc).isoformat(),
            updated_time=datetime.now(timezone.utc).isoformat(),
            checksums=[Checksum(checksum="1", type="md5")],
            access_methods=[
                AccessMethod(access_url=AccessURL(url=download_url), type="s3")
            ],
        )

    raise HTTPException(
        status_code=404,
        detail=(f'The DRSObject with the id "{file_id}" does not exist.'),
    )


@app.get(
    "/presigned_post/{file_id}", summary="ulc_presigned_post_mock", status_code=200
)
async def ulc_presigned_post(file_id: str):

    """
    Mock for the ulc /presigned_post/{file_id} call.
    """

    upload_url = "test"

    if file_id == "1":
        return {"presigned_post": upload_url}

    raise HTTPException(
        status_code=404,
        detail=(f'The file with the file_id "{file_id}" does not exist.'),
    )


@app.patch(
    "/confirm_upload/{file_id}", summary="ulc_confirm_upload_mock", status_code=204
)
async def ulc_confirm_upload(file_id: str, state: State):

    """
    Mock for the drs3 /confirm_upload/{file_id} call
    """

    if file_id == "1":
        if state.state == UploadState.REGISTERED:
            return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

        raise HTTPException(
            status_code=400,
            detail=(f'The file with id "{file_id}" can`t be set to "{state}"'),
        )

    raise HTTPException(
        status_code=400,
        detail=(
            f'The file with id "{file_id}" is registered for upload'
            + " but its content was not found in the inbox."
        ),
    )
