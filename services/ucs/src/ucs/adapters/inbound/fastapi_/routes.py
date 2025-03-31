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

"""Module containing the main FastAPI router and all route functions."""

from typing import Annotated

from fastapi import APIRouter, Path, status

from ucs.adapters.inbound.fastapi_ import dummies, http_exceptions, rest_models
from ucs.ports.inbound.file_service import FileMetadataServicePort
from ucs.ports.inbound.upload_service import UploadServicePort

router = APIRouter(tags=["UploadControllerService"])


ERROR_RESPONSES = {
    "noFileAccess": {
        "description": (
            "Exceptions by ID:"
            + "\n- noFileAccess: The user is not registered as a Data Submitter for the"
            + " corresponding file."
            ""
        ),
        "model": http_exceptions.HttpNoFileAccessError.get_body_model(),
    },
    "noSuchUpload": {
        "description": (
            "Exceptions by ID:"
            + "\n- noSuchUpload: The multi-part upload with the given ID does not"
            + " exist."
        ),
        "model": http_exceptions.HttpUploadNotFoundError.get_body_model(),
    },
    "noSuchStorage": {
        "description": (
            "Exceptions by ID:"
            + "\n- noSuchStorage: The storage node for the given alias does not exist."
        ),
        "model": http_exceptions.HttpUnknownStorageAliasError.get_body_model(),
    },
    "fileNotRegistered": {
        "description": (
            "Exceptions by ID:"
            + "\n- fileNotRegistered: The file with the given ID has not (yet) been"
            + " registered for upload."
        ),
        "model": http_exceptions.HttpFileNotFoundError.get_body_model(),
    },
}


@router.get(
    "/health",
    summary="health",
    status_code=status.HTTP_200_OK,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.get(
    "/files/{file_id}",
    summary="Get file metadata including the current upload attempt.",
    operation_id="getFileMetadata",
    status_code=status.HTTP_200_OK,
    response_model=rest_models.FileMetadata,
    response_description="File metadata including the current upload attempt",
    responses={
        status.HTTP_403_FORBIDDEN: ERROR_RESPONSES["noFileAccess"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["fileNotRegistered"],
    },
)
async def get_file_metadata(
    file_id: str,
    file_metadata_service: dummies.FileMetadataServiceDummy,
):
    """Get file metadata including the current upload attempt."""
    try:
        return await file_metadata_service.get_by_id(file_id)
    except FileMetadataServicePort.FileUnknownError as error:
        raise http_exceptions.HttpFileNotFoundError(file_id=file_id) from error


@router.post(
    "/uploads",
    summary="Initiate a new multi-part upload.",
    operation_id="createUpload",
    response_model=rest_models.UploadAttempt,
    status_code=status.HTTP_200_OK,
    response_description="Details on the newly created upload.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "Exceptions by ID:"
                + "\n- existingActiveUpload: Imposible to create a new upload for"
                + " the file with the specific ID. There is already another"
                + " active or accepted upload for that file. Details on the"
                + " existing upload are provided as part of the exception data."
                + "\n- fileNotRegistered: The file with the given ID has not (yet) been"
                + " registered for upload."
            ),
            "model": http_exceptions.HttpExistingActiveUploadError.get_body_model()
            | http_exceptions.HttpFileNotFoundUploadError.get_body_model(),
        },
        status.HTTP_403_FORBIDDEN: ERROR_RESPONSES["noFileAccess"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["noSuchStorage"],
    },
)
async def create_upload(
    upload_creation: rest_models.UploadAttemptCreation,
    upload_service: dummies.UploadServiceDummy,
):
    """Initiate a new multi-part upload for the given file."""
    storage_alias = upload_creation.storage_alias

    try:
        return await upload_service.initiate_new(
            file_id=upload_creation.file_id,
            submitter_public_key=upload_creation.submitter_public_key,
            storage_alias=storage_alias,
        )
    except UploadServicePort.ExistingActiveUploadError as error:
        raise http_exceptions.HttpExistingActiveUploadError(
            file_id=upload_creation.file_id,
            active_upload=error.active_upload,
        ) from error
    except UploadServicePort.UnknownStorageAliasError as error:
        raise http_exceptions.HttpUnknownStorageAliasError(
            storage_alias=storage_alias
        ) from error
    except FileMetadataServicePort.FileUnknownError as error:
        raise http_exceptions.HttpFileNotFoundUploadError(
            file_id=upload_creation.file_id, status_code=400
        ) from error


@router.get(
    "/uploads/{upload_id}",
    summary="Get details on a specific upload.",
    operation_id="getUploadDetails",
    status_code=status.HTTP_200_OK,
    response_model=rest_models.UploadAttempt,
    response_description="Details on a specific upload.",
    responses={
        status.HTTP_403_FORBIDDEN: ERROR_RESPONSES["noFileAccess"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["noSuchUpload"],
    },
)
async def get_upload(
    upload_id: str,
    upload_service: dummies.UploadServiceDummy,
):
    """Get details on a specific upload."""
    try:
        return await upload_service.get_details(upload_id=upload_id)
    except UploadServicePort.UnknownUploadError as error:
        raise http_exceptions.HttpUploadNotFoundError(upload_id=upload_id) from error


@router.patch(
    "/uploads/{upload_id}",
    summary="Update the status of an existing multi-part upload.",
    operation_id="updateUploadStatus",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Multi-part upload successfully updated.",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "Exceptions by ID:"
                + "\n- uploadNotPending:"
                + " The corresponding upload is not in 'pending' state."
                + " Thus no updates can be performed."
                + " Details on the current upload status can be found in"
                + " the exception data."
                + "\n- uploadStatusChange:"
                + " Failed to change the status of upload."
                + " A reason is provided in the description."
            ),
            "model": http_exceptions.HttpUploadNotPendingError.get_body_model()
            | http_exceptions.HttpUploadStatusChangeError.get_body_model(),
        },
        status.HTTP_403_FORBIDDEN: ERROR_RESPONSES["noFileAccess"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["noSuchUpload"],
    },
)
async def update_upload_status(
    upload_id: str,
    update: rest_models.UploadAttemptUpdate,
    upload_service: dummies.UploadServiceDummy,
):
    """
    Declare a multi-part upload as complete by setting its status to "uploaded".
    Or cancel a multi-part upload by setting its status to "cancelled".
    """
    try:
        if update.status == "uploaded":
            await upload_service.complete(upload_id=upload_id)
        else:
            await upload_service.cancel(upload_id=upload_id)
    except UploadServicePort.UploadStatusMismatchError as error:
        raise http_exceptions.HttpUploadNotPendingError(
            upload_id=upload_id, current_status=error.current_status
        ) from error
    except UploadServicePort.UploadCompletionError as error:
        raise http_exceptions.HttpUploadStatusChangeError(
            upload_id=upload_id,
            target_status=rest_models.UploadStatus.UPLOADED,
            reason=error.reason,
        ) from error
    except UploadServicePort.UploadCancelError as error:
        raise http_exceptions.HttpUploadStatusChangeError(
            upload_id=upload_id,
            target_status=rest_models.UploadStatus.CANCELLED,
            reason=error.possible_reason,
        ) from error
    except UploadServicePort.UnknownUploadError as error:
        raise http_exceptions.HttpUploadNotFoundError(upload_id=upload_id) from error


@router.post(
    "/uploads/{upload_id}/parts/{part_no}/signed_urls",
    summary="Create new pre-signed URL for a specific part.",
    operation_id="createPreSignedURL",
    status_code=status.HTTP_200_OK,
    response_model=rest_models.PartUploadDetails,
    response_description="The newly created pre-signed URL.",
    responses={
        status.HTTP_403_FORBIDDEN: ERROR_RESPONSES["noFileAccess"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["noSuchUpload"],
    },
)
async def create_presigned_url(
    upload_id: str,
    part_no: Annotated[int, Path(..., ge=1, le=10000)],
    upload_service: dummies.UploadServiceDummy,
):
    """
    Create a pre-signed URL for the specified part number of the specified multi-part
    upload.
    """
    try:
        presigned_url = await upload_service.create_part_url(
            upload_id=upload_id, part_no=part_no
        )
    except UploadServicePort.UnknownUploadError as error:
        raise http_exceptions.HttpUploadNotFoundError(upload_id=upload_id) from error

    return rest_models.PartUploadDetails(url=presigned_url)
