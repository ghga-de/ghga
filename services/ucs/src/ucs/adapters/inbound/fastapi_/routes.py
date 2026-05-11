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
from ucs.core.models import FileUpload
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
    "boxStateError": {
        "description": (
            "Exceptions by ID:"
            + "\n- boxStateError: The FileUploadBox's state precludes the requested action."
        ),
        "model": http_exceptions.HttpBoxStateError.get_body_model(),
    },
    "boxVersionOutdated": {
        "description": (
            "Exceptions by ID:"
            + "\n- boxVersionOutdated: The requested FileUploadBox version is outdated."
        ),
        "model": http_exceptions.HttpBoxVersionError.get_body_model(),
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
    "boxMaxSizeExceeded": {
        "description": (
            "Exceptions by ID:"
            + "\n- boxMaxSizeExceeded: Adding this file would exceed the box's size limit."
        ),
        "model": http_exceptions.HttpBoxMaxSizeExceededError.get_body_model(),
    },
    "boxMaxSizeTooLow": {
        "description": (
            "Exceptions by ID:"
            + "\n- boxMaxSizeTooLow: The requested max_size is less than the"
            + " box's current committed size."
        ),
        "model": http_exceptions.HttpMaxSizeTooLowError.get_body_model(),
    },
    "tooManyOpenUploads": {
        "description": (
            "Exceptions by ID:"
            + "\n- tooManyOpenUploads: The box already has the maximum number"
            + " of concurrent in-progress uploads."
        ),
        "model": http_exceptions.HttpTooManyOpenUploadsError.get_body_model(),
    },
}

# For the update_box endpoint, map the work type required to change to a given box state
BOX_STATE_TO_WORK_TYPE: dict[str, str] = {
    "open": "unlock",
    "locked": "lock",
    "archived": "archive",
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
        return await upload_controller.create_file_upload_box(
            storage_alias=box_creation.storage_alias,
            max_size=box_creation.max_size,
        )
    except UploadControllerPort.UnknownStorageAliasError as error:
        raise http_exceptions.HttpUnknownStorageAliasError() from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error


@router.patch(
    "/boxes/{box_id}",
    summary="Update a FileUploadBox (lock/unlock/archive/resize)",
    operation_id="updateBox",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="FileUploadBox successfully updated",
    responses={
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["boxNotFound"],
        status.HTTP_409_CONFLICT: ERROR_RESPONSES["boxVersionOutdated"]
        | ERROR_RESPONSES["boxMaxSizeTooLow"],
    },
)
@TRACER.start_as_current_span("routes.update_box")
async def update_box(  # noqa: C901, PLR0912
    box_id: UUID4,
    box_update: rest_models.BoxUpdateRequest,
    work_order: Annotated[
        rest_models.ChangeFileBoxWorkOrder,
        http_authorization.require_change_file_box_work_order,
    ],
    upload_controller: dummies.UploadControllerDummy,
) -> None:
    """Update a FileUploadBox state or max_size.

    Request body must contain a `version` field (for optimistic locking) plus either
    a `state` field indicating the target state or a `max_size` field with the
    new size limit. Requires ChangeFileBoxWorkOrder token from the UOS. When updating
    state, the work type must match the target state. When updating max_size, the
    work type must be 'resize'. Users are only allowed to lock the box; a Data Steward
    role is required to do everything else.
    """
    if box_update.state is not None:
        required_work_type = BOX_STATE_TO_WORK_TYPE.get(box_update.state)
        if not required_work_type:
            raise http_exceptions.HttpNotAuthorizedError()
    else:  # the validator guarantees that max_size is set in this case
        required_work_type = "resize"

    if work_order.box_id != box_id or work_order.work_type != required_work_type:
        raise http_exceptions.HttpNotAuthorizedError()

    try:
        if box_update.max_size is not None:
            await upload_controller.update_box_max_size(
                box_id=box_id, version=box_update.version, max_size=box_update.max_size
            )
        else:
            match box_update.state:
                case "locked":
                    await upload_controller.lock_file_upload_box(
                        box_id=box_id, version=box_update.version
                    )
                case "open":
                    await upload_controller.unlock_file_upload_box(
                        box_id=box_id, version=box_update.version
                    )
                case "archived":
                    await upload_controller.archive_file_upload_box(
                        box_id=box_id, version=box_update.version
                    )
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except UploadControllerPort.BoxVersionError as error:
        raise http_exceptions.HttpBoxVersionError(box_id=box_id) from error
    except UploadControllerPort.BoxMaxSizeTooLowError as error:
        raise http_exceptions.HttpMaxSizeTooLowError(
            box_id=box_id, max_size=error.max_size, current_size=error.current_size
        ) from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error


@router.get(
    "/boxes/{box_id}/uploads",
    summary="Retrieve list of file IDs for box",
    operation_id="getBoxUploads",
    status_code=status.HTTP_200_OK,
    response_model=list[FileUpload],
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
) -> list[FileUpload]:
    """Retrieve list of FileUploads for a FileUploadBox.

    Returns the list of FileUploads for completed uploads in the specified box.
    Requires ViewFileBoxWorkOrder token from the UOS.
    """
    if work_order.box_id != box_id:
        raise http_exceptions.HttpNotAuthorizedError()

    try:
        file_uploads = await upload_controller.get_box_file_info(box_id=box_id)
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error

    return file_uploads


@router.post(
    "/boxes/{box_id}/uploads",
    summary="Add a new FileUpload to an existing FileUploadBox",
    operation_id="createFileUpload",
    status_code=status.HTTP_201_CREATED,
    response_model=rest_models.FileUploadCreationResponse,
    response_description="The file_id of the newly created FileUpload",
    responses={
        status.HTTP_400_BAD_REQUEST: ERROR_RESPONSES["noSuchStorage"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["boxNotFound"],
        status.HTTP_409_CONFLICT: ERROR_RESPONSES["boxStateError"]
        | ERROR_RESPONSES["fileUploadAlreadyExists"]
        | ERROR_RESPONSES["orphanedMultipartUpload"],
        status.HTTP_507_INSUFFICIENT_STORAGE: ERROR_RESPONSES["boxMaxSizeExceeded"],
        status.HTTP_429_TOO_MANY_REQUESTS: ERROR_RESPONSES["tooManyOpenUploads"],
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
) -> rest_models.FileUploadCreationResponse:
    """Add a new FileUpload to an existing FileUploadBox.

    Creates a new file upload within the specified box with the provided alias, checksum, and size.
    Initiates a multipart upload and returns the file ID, file alias, and storage alias
    for the newly created upload. The file alias may be used by clients to ensure the
    response pertains to the correct file.

    Requires a CreateFileWorkOrder token from the WPS.
    """
    file_alias = file_upload_creation.alias
    if work_order.box_id != box_id or work_order.alias != file_alias:
        raise http_exceptions.HttpNotAuthorizedError()

    try:
        file_id, storage_alias = await upload_controller.initiate_file_upload(
            box_id=box_id,
            alias=file_alias,
            decrypted_size=file_upload_creation.decrypted_size,
            encrypted_size=file_upload_creation.encrypted_size,
            part_size=file_upload_creation.part_size,
        )
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except UploadControllerPort.BoxStateError as error:
        raise http_exceptions.HttpBoxStateError(
            box_id=box_id, box_state=error.box_state
        ) from error
    except UploadControllerPort.BoxMaxSizeExceededError as error:
        raise http_exceptions.HttpBoxMaxSizeExceededError(
            box_id=box_id,
            max_size=error.max_size,
            current_size=error.current_size,
            file_alias=file_alias,
        ) from error
    except UploadControllerPort.TooManyOpenUploadsError as error:
        raise http_exceptions.HttpTooManyOpenUploadsError(
            box_id=box_id,
            max_concurrent=error.max_concurrent,
        ) from error
    except UploadControllerPort.FileUploadAlreadyExists as error:
        raise http_exceptions.HttpFileUploadAlreadyExistsError(
            alias=file_alias
        ) from error
    except UploadControllerPort.UnknownStorageAliasError as error:
        # This should not happen in normal operation since the box was already created
        # with a valid storage alias, but handle it just in case
        raise http_exceptions.HttpUnknownStorageAliasError() from error
    except UploadControllerPort.UploadAlreadyInProgressError as error:
        raise http_exceptions.HttpOrphanedMultipartUploadError(
            file_alias=file_alias
        ) from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error

    response_payload = rest_models.FileUploadCreationResponse(
        file_id=file_id, alias=file_alias, storage_alias=storage_alias
    )
    return response_payload


@router.get(
    "/boxes/{box_id}/uploads/{file_id}/parts/{part_no}",
    summary="Get pre-signed S3 upload URL for file part",
    operation_id="getPartUploadUrl",
    status_code=status.HTTP_200_OK,
    response_model=str,
    response_description="The pre-signed URL for uploading the file part",
    responses={
        status.HTTP_400_BAD_REQUEST: ERROR_RESPONSES["noSuchStorage"],
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["fileUploadNotFound"]
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
    except UploadControllerPort.FileUploadNotFound as error:
        raise http_exceptions.HttpFileUploadNotFoundError(file_id=file_id) from error
    except UploadControllerPort.UnknownStorageAliasError as error:
        raise http_exceptions.HttpUnknownStorageAliasError() from error
    except UploadControllerPort.UploadSessionNotFoundError as error:
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
        | ERROR_RESPONSES["fileUploadNotFound"],
        status.HTTP_409_CONFLICT: ERROR_RESPONSES["boxStateError"],
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
            unencrypted_checksum=file_upload_completion.decrypted_sha256,
            encrypted_checksum=file_upload_completion.encrypted_md5,
            encrypted_parts_md5=file_upload_completion.encrypted_parts_md5,
            encrypted_parts_sha256=file_upload_completion.encrypted_parts_sha256,
        )
    except UploadControllerPort.BoxNotFoundError as error:
        raise http_exceptions.HttpBoxNotFoundError(box_id=box_id) from error
    except UploadControllerPort.BoxStateError as error:
        raise http_exceptions.HttpBoxStateError(
            box_id=box_id, box_state=error.box_state
        ) from error
    except UploadControllerPort.FileUploadNotFound as error:
        raise http_exceptions.HttpFileUploadNotFoundError(file_id=file_id) from error
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
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["boxNotFound"],
        status.HTTP_409_CONFLICT: ERROR_RESPONSES["boxStateError"],
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
    except UploadControllerPort.BoxStateError as error:
        raise http_exceptions.HttpBoxStateError(
            box_id=box_id, box_state=error.box_state
        ) from error
    except UploadControllerPort.UnknownStorageAliasError as error:
        raise http_exceptions.HttpUnknownStorageAliasError() from error
    except UploadControllerPort.UploadAbortError as error:
        raise http_exceptions.HttpUploadAbortError() from error
    except Exception as error:
        log.error(error, exc_info=True)
        raise http_exceptions.HttpInternalError() from error
