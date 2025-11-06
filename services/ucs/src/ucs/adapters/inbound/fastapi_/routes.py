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

import logging
from typing import Annotated

from fastapi import APIRouter, status
from pydantic import UUID4

from ucs.adapters.inbound.fastapi_ import (
    dummies,
    http_authorization,
    http_exceptions,
    rest_models,
)
from ucs.constants import TRACER
from ucs.ports.inbound.controller import UploadControllerPort

router = APIRouter(tags=["UploadControllerService"])

log = logging.getLogger(__name__)

ERROR_RESPONSES = {
    "noSuchStorage": {
        "description": (
            "Exceptions by ID:"
            + "\n- noSuchStorage: The storage node for the given alias does not exist."
        ),
        "model": http_exceptions.HttpUnknownStorageAliasError.get_body_model(),
    },
    "boxNotFound": {
        "description": (
            "Exceptions by ID:"
            + "\n- boxNotFound: The FileUploadBox with the given ID does not exist."
        ),
        "model": http_exceptions.HttpBoxNotFoundError.get_body_model(),
    },
    "lockedBox": {
        "description": (
            "Exceptions by ID:"
            + "\n- lockedBox: The FileUploadBox is locked and cannot be modified."
        ),
        "model": http_exceptions.HttpLockedBoxError.get_body_model(),
    },
    "fileUploadAlreadyExists": {
        "description": (
            "Exceptions by ID:"
            + "\n- fileUploadAlreadyExists: A FileUpload with the given alias already exists in this box."
        ),
        "model": http_exceptions.HttpFileUploadAlreadyExistsError.get_body_model(),
    },
    "orphanedMultipartUpload": {
        "description": (
            "Exceptions by ID:"
            + "\n- orphanedMultipartUpload: A multipart upload is already in progress"
            + " for this file but cannot be aborted. Request file deletion and then"
            + " attempt the upload again."
        ),
        "model": http_exceptions.HttpOrphanedMultipartUploadError.get_body_model(),
    },
    "s3UploadDetailsNotFound": {
        "description": (
            "Exceptions by ID:"
            + "\n- s3UploadDetailsNotFound: S3 upload details for the file could not be found."
        ),
        "model": http_exceptions.HttpS3UploadDetailsNotFoundError.get_body_model(),
    },
    "s3UploadNotFound": {
        "description": (
            "Exceptions by ID:"
            + "\n- s3UploadNotFound: The S3 multipart upload could not be found."
        ),
        "model": http_exceptions.HttpS3UploadNotFoundError.get_body_model(),
    },
    "fileUploadNotFound": {
        "description": (
            "Exceptions by ID:"
            + "\n- fileUploadNotFound: The FileUpload could not be found."
        ),
        "model": http_exceptions.HttpFileUploadNotFoundError.get_body_model(),
    },
    "s3UploadCompletionFailure": {
        "description": (
            "Exceptions by ID:"
            + "\n- s3UploadCompletionFailure: There was an error completing the s3"
            + " multipart upload. Delete the file from the file upload box and retry."
        ),
        "model": http_exceptions.HttpUploadCompletionError.get_body_model(),
    },
    "uploadAbortError": {
        "description": (
            "Exceptions by ID:"
            + "\n- uploadAbortError: There was an error aborting the s3"
            + " multipart upload."
        ),
        "model": http_exceptions.HttpUploadAbortError.get_body_model(),
    },
    "checksumMismatch": {
        "description": (
            "Exceptions by ID:"
            + "\n- checksumMismatch: The user-supplied encrypted checksum doesn't match S3."
        ),
        "model": http_exceptions.HttpChecksumMismatchError.get_body_model(),
    },
}


@router.get(
    "/health",
    summary="health",
    status_code=status.HTTP_200_OK,
)
@TRACER.start_as_current_span("routes.health")
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.post(
    "/boxes",
    summary="Create a new FileUploadBox",
    operation_id="createBox",
    status_code=status.HTTP_201_CREATED,
    response_model=UUID4,
    response_description="The box_id of the newly created FileUploadBox",
    responses={status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["noSuchStorage"]},
)
@TRACER.start_as_current_span("routes.create_box")
async def create_box(
    box_creation: rest_models.BoxCreationRequest,
    work_order: Annotated[
        rest_models.CreateFileBoxWorkOrder,
        http_authorization.require_create_file_box_work_order,
    ],
    upload_controller: dummies.UploadControllerDummy,
) -> UUID4:
    """Create a new FileUploadBox.

    Requires CreateFileBoxWorkOrder token and only allowed for Data Stewards via the UOS.
    Request body should contain the storage alias to use for uploads within the box.
    Returns the box_id of the newly created FileUploadBox.
    """
    try:
        alias = box_creation.storage_alias
        return await upload_controller.create_file_upload_box(storage_alias=alias)
    except UploadControllerPort.UnknownStorageAliasError as error:
        raise http_exceptions.HttpUnknownStorageAliasError() from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error


@router.patch(
    "/boxes/{box_id}",
    summary="Update a FileUploadBox (lock/unlock)",
    operation_id="updateBox",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="FileUploadBox successfully updated",
    responses={
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["boxNotFound"],
    },
)
@TRACER.start_as_current_span("routes.update_box")
async def update_box(
    box_id: UUID4,
    box_update: rest_models.BoxUpdateRequest,
    work_order: Annotated[
        rest_models.ChangeFileBoxWorkOrder,
        http_authorization.require_change_file_box_work_order,
    ],
    upload_controller: dummies.UploadControllerDummy,
) -> None:
    """Update a FileUploadBox to lock or unlock it.

    Request body must indicate whether the box is meant to be locked or unlocked.
    Requires ChangeFileBoxWorkOrder token from the UOS. Users are only allowed to lock
    the box; a Data Steward role is required to unlock it.
    """
    required_work_type = "lock" if box_update.lock else "unlock"
    if work_order.box_id != box_id:
        raise http_exceptions.HttpNotAuthorizedError()
    elif work_order.work_type != required_work_type:
        raise http_exceptions.HttpNotAuthorizedError(status_code=401)

    try:
        if box_update.lock:
            await upload_controller.lock_file_upload_box(box_id=box_id)
        else:
            await upload_controller.unlock_file_upload_box(box_id=box_id)
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error


@router.get(
    "/boxes/{box_id}/uploads",
    summary="Retrieve list of file IDs for box",
    operation_id="getBoxUploads",
    status_code=status.HTTP_200_OK,
    response_model=rest_models.BoxUploadsResponse,
    response_description="List of file IDs for completed uploads in the box",
    responses={
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["boxNotFound"],
    },
)
@TRACER.start_as_current_span("routes.get_box_uploads")
async def get_box_uploads(
    box_id: UUID4,
    work_order: Annotated[
        rest_models.ViewFileBoxWorkOrder,
        http_authorization.require_view_file_box_work_order,
    ],
    upload_controller: dummies.UploadControllerDummy,
):
    """Retrieve list of file IDs for a FileUploadBox.

    Returns the list of file IDs for completed uploads in the specified box.
    Requires ViewFileBoxWorkOrder token from the UOS.
    """
    if work_order.box_id != box_id:
        raise http_exceptions.HttpNotAuthorizedError()

    try:
        file_ids = await upload_controller.get_file_ids_for_box(box_id=box_id)
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error

    return rest_models.BoxUploadsResponse(file_ids=file_ids)


@router.post(
    "/boxes/{box_id}/uploads",
    summary="Add a new FileUpload to an existing FileUploadBox",
    operation_id="createFileUpload",
    status_code=status.HTTP_201_CREATED,
    response_model=UUID4,
    response_description="The file_id of the newly created FileUpload",
    responses={
        status.HTTP_400_BAD_REQUEST: ERROR_RESPONSES["noSuchStorage"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["boxNotFound"],
        status.HTTP_409_CONFLICT: ERROR_RESPONSES["lockedBox"]
        | ERROR_RESPONSES["fileUploadAlreadyExists"]
        | ERROR_RESPONSES["orphanedMultipartUpload"],
    },
)
@TRACER.start_as_current_span("routes.create_file_upload")
async def create_file_upload(
    box_id: UUID4,
    file_upload_creation: rest_models.FileUploadCreationRequest,
    work_order: Annotated[
        rest_models.CreateFileWorkOrder,
        http_authorization.require_create_file_work_order,
    ],
    upload_controller: dummies.UploadControllerDummy,
) -> UUID4:
    """Add a new FileUpload to an existing FileUploadBox.

    Creates a new file upload within the specified box with the provided alias, checksum, and size.
    Initiates a multipart upload and returns the file ID for the newly created upload.
    Requires a CreateFileWorkOrder token from the WPS.
    """
    file_alias = file_upload_creation.alias
    if work_order.box_id != box_id or work_order.alias != file_alias:
        raise http_exceptions.HttpNotAuthorizedError()

    try:
        file_id = await upload_controller.initiate_file_upload(
            box_id=box_id,
            alias=file_alias,
            size=file_upload_creation.size,
        )
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except UploadControllerPort.LockedBoxError as error:
        raise http_exceptions.HttpLockedBoxError(box_id=box_id) from error
    except UploadControllerPort.FileUploadAlreadyExists as error:
        raise http_exceptions.HttpFileUploadAlreadyExistsError(
            alias=file_alias
        ) from error
    except UploadControllerPort.UnknownStorageAliasError as error:
        # This should not happen in normal operation since the box was already created
        # with a valid storage alias, but handle it just in case
        raise http_exceptions.HttpUnknownStorageAliasError() from error
    except UploadControllerPort.OrphanedMultipartUploadError as error:
        raise http_exceptions.HttpOrphanedMultipartUploadError(
            file_alias=file_alias
        ) from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error

    return file_id


@router.get(
    "/boxes/{box_id}/uploads/{file_id}/parts/{part_no}",
    summary="Get pre-signed S3 upload URL for file part",
    operation_id="getPartUploadUrl",
    status_code=status.HTTP_200_OK,
    response_model=str,
    response_description="The pre-signed URL for uploading the file part",
    responses={
        status.HTTP_400_BAD_REQUEST: ERROR_RESPONSES["noSuchStorage"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["s3UploadDetailsNotFound"]
        | ERROR_RESPONSES["s3UploadNotFound"],
    },
)
@TRACER.start_as_current_span("routes.get_part_upload_url")
async def get_part_upload_url(
    box_id: UUID4,
    file_id: UUID4,
    part_no: int,
    work_order: Annotated[
        rest_models.UploadFileWorkOrder,
        http_authorization.require_upload_file_work_order,
    ],
    upload_controller: dummies.UploadControllerDummy,
) -> str:
    """Get pre-signed S3 upload URL for a specific file part.

    Returns a pre-signed URL that can be used to upload the bytes for the specified
    part number of the specified file upload.
    Requires an UploadFileWorkOrder token from the WPS.
    """
    if work_order.box_id != box_id or work_order.file_id != file_id:
        raise http_exceptions.HttpNotAuthorizedError()
    elif work_order.work_type != "upload":
        raise http_exceptions.HttpNotAuthorizedError(status_code=401)

    try:
        presigned_url = await upload_controller.get_part_upload_url(
            file_id=file_id, part_no=part_no
        )
    except UploadControllerPort.S3UploadDetailsNotFoundError as error:
        raise http_exceptions.HttpS3UploadDetailsNotFoundError(
            file_id=file_id
        ) from error
    except UploadControllerPort.UnknownStorageAliasError as error:
        raise http_exceptions.HttpUnknownStorageAliasError() from error
    except UploadControllerPort.S3UploadNotFoundError as error:
        raise http_exceptions.HttpS3UploadNotFoundError() from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error

    return presigned_url


@router.patch(
    "/boxes/{box_id}/uploads/{file_id}",
    summary="Complete file upload",
    operation_id="completeFileUpload",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="File upload completed successfully",
    responses={
        status.HTTP_400_BAD_REQUEST: ERROR_RESPONSES["checksumMismatch"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["boxNotFound"]
        | ERROR_RESPONSES["s3UploadDetailsNotFound"]
        | ERROR_RESPONSES["fileUploadNotFound"],
        status.HTTP_409_CONFLICT: ERROR_RESPONSES["lockedBox"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: ERROR_RESPONSES[
            "s3UploadCompletionFailure"
        ],
    },
)
@TRACER.start_as_current_span("routes.complete_file_upload")
async def complete_file_upload(
    box_id: UUID4,
    file_id: UUID4,
    file_upload_completion: rest_models.FileUploadCompletionRequest,
    work_order: Annotated[
        rest_models.CloseFileWorkOrder,
        http_authorization.require_close_file_work_order,
    ],
    upload_controller: dummies.UploadControllerDummy,
) -> None:
    """Complete file upload by instructing S3 to finalize the multipart upload.

    Concludes the file upload process in UCS by instructing S3 to complete the
    multipart upload for the specified file.
    Requires a CloseFileWorkOrder token from the WPS.
    """
    if work_order.box_id != box_id or work_order.file_id != file_id:
        raise http_exceptions.HttpNotAuthorizedError()

    try:
        await upload_controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum=file_upload_completion.unencrypted_checksum,
            encrypted_checksum=file_upload_completion.encrypted_checksum,
        )
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except UploadControllerPort.LockedBoxError as error:
        raise http_exceptions.HttpLockedBoxError(box_id=box_id) from error
    except UploadControllerPort.FileUploadNotFound as error:
        raise http_exceptions.HttpFileUploadNotFoundError(file_id=file_id) from error
    except UploadControllerPort.S3UploadDetailsNotFoundError as error:
        raise http_exceptions.HttpS3UploadDetailsNotFoundError(
            file_id=file_id
        ) from error
    except UploadControllerPort.UploadCompletionError as error:
        raise http_exceptions.HttpUploadCompletionError(
            box_id=box_id, file_id=file_id
        ) from error
    except UploadControllerPort.ChecksumMismatchError as error:
        raise http_exceptions.HttpChecksumMismatchError(file_id=file_id) from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error


@router.delete(
    "/boxes/{box_id}/uploads/{file_id}",
    summary="Remove a FileUpload from the FileUploadBox",
    operation_id="removeFileUpload",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="FileUpload removed successfully",
    responses={
        status.HTTP_400_BAD_REQUEST: ERROR_RESPONSES["noSuchStorage"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["boxNotFound"]
        | ERROR_RESPONSES["s3UploadDetailsNotFound"],
        status.HTTP_409_CONFLICT: ERROR_RESPONSES["lockedBox"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: ERROR_RESPONSES["uploadAbortError"],
    },
)
@TRACER.start_as_current_span("routes.remove_file_upload")
async def remove_file_upload(
    box_id: UUID4,
    file_id: UUID4,
    work_order: Annotated[
        rest_models.DeleteFileWorkOrder,
        http_authorization.require_delete_file_work_order,
    ],
    upload_controller: dummies.UploadControllerDummy,
) -> None:
    """Remove a FileUpload from the FileUploadBox.

    Deletes the FileUpload and tells S3 to cancel the multipart upload if applicable.
    Requires a DeleteFileWorkOrder token from the WPS.
    """
    if work_order.box_id != box_id or work_order.file_id != file_id:
        raise http_exceptions.HttpNotAuthorizedError()

    try:
        await upload_controller.remove_file_upload(box_id=box_id, file_id=file_id)
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except UploadControllerPort.LockedBoxError as error:
        raise http_exceptions.HttpLockedBoxError(box_id=box_id) from error
    except UploadControllerPort.S3UploadDetailsNotFoundError as error:
        raise http_exceptions.HttpS3UploadDetailsNotFoundError(
            file_id=file_id
        ) from error
    except UploadControllerPort.UnknownStorageAliasError as error:
        raise http_exceptions.HttpUnknownStorageAliasError() from error
    except UploadControllerPort.UploadAbortError as error:
        raise http_exceptions.HttpUploadAbortError() from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error
