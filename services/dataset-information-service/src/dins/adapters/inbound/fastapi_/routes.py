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
"""FastAPI routes for S3 upload metadata ingest"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from dins.adapters.inbound.fastapi_ import dummies, http_exceptions, http_responses
from dins.core import models
from dins.ports.inbound.information_service import InformationServicePort

router = APIRouter()

RESPONSES = {
    "fileInformation": {
        "description": (
            "A configuration or external communication error has occurred and details "
            + "should not be communicated to the client"
        ),
        "model": models.FileInformation,
    },
    "informationNotFound": {
        "description": (
            "Exceptions by ID:\n- informationNotFound: No information registered for the given ID."
        ),
        "model": http_exceptions.HttpInformationNotFoundError.get_body_model(),
    },
}


@router.get(
    "/health",
    summary="health",
    tags=["FileIngestService"],
    status_code=200,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.get(
    "/file_information/{file_id}",
    summary="Return public file information for the given file id, i.e. public accession.",
    operation_id="getFileInformation",
    tags=["FileIngestService"],
    status_code=status.HTTP_200_OK,
    response_description="File information consisting of file id, sha256 checksum of"
    " the unencrypted file content and file size of the unencrypted file in bytes.",
    responses={
        status.HTTP_200_OK: RESPONSES["fileInformation"],
        status.HTTP_404_NOT_FOUND: RESPONSES["informationNotFound"],
    },
)
async def get_file_information(
    file_id: str,
    information_service: Annotated[
        InformationServicePort, Depends(dummies.information_service_port)
    ],
):
    """Retrieve and serve stored file information."""
    try:
        file_information = await information_service.serve_information(file_id=file_id)
    except information_service.InformationNotFoundError as error:
        raise http_exceptions.HttpInformationNotFoundError(file_id=file_id) from error

    return http_responses.HttpFileInformationResponse(file_information=file_information)
