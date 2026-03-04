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


"""Module containing the main FastAPI router and all route functions."""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import UUID4

from wps.adapters.inbound.fastapi_.auth import UserAuthContext, WorkPackageAccessToken
from wps.adapters.inbound.fastapi_.dummies import WorkPackageRepositoryDummy
from wps.constants import TRACER, WORK_ORDER_TOKEN_VALID_SECONDS
from wps.core.models import (
    BoxWithExpiration,
    Dataset,
    DatasetWithExpiration,
    UploadWorkOrderTokenRequest,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
    WorkPackageDetails,
)

__all__ = ["router"]

log = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    summary="health",
    tags=["WorkPackages"],
    status_code=status.HTTP_200_OK,
)
@TRACER.start_as_current_span("routes.health")
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.post(
    "/work-packages",
    operation_id="create_work_package",
    tags=["WorkPackages"],
    summary="Create a work package",
    description="Endpoint used to create a new work package",
    responses={
        201: {
            "model": WorkPackageCreationResponse,
            "description": "Work package was successfully created.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to create a work package."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
@TRACER.start_as_current_span("routes.create_work_package")
async def create_work_package(
    creation_data: WorkPackageCreationData,
    repository: WorkPackageRepositoryDummy,
    auth_context: UserAuthContext,
) -> WorkPackageCreationResponse:
    """Create a work package using an internal auth token with a user context."""
    try:
        return await repository.create(
            creation_data=creation_data, auth_context=auth_context
        )
    except repository.WorkPackageAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.get(
    "/work-packages/{work_package_id}",
    operation_id="get_work_package",
    tags=["WorkPackages"],
    summary="Get a work package",
    description="Endpoint used to get work package details",
    responses={
        200: {
            "model": WorkPackageDetails,
            "description": "Work package details have been found.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to get the work package."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("routes.get_work_package")
async def get_work_package(
    work_package_id: UUID4,
    repository: WorkPackageRepositoryDummy,
    work_package_access_token: WorkPackageAccessToken,
) -> WorkPackageDetails:
    """Get work package details using a work package access token."""
    try:
        if not (work_package_id and work_package_access_token):
            raise repository.WorkPackageAccessError
        package = await repository.get(
            work_package_id,
            check_valid=True,
            work_package_access_token=work_package_access_token,
        )
    except repository.WorkPackageAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return WorkPackageDetails(
        type=package.type,
        files=package.files,
        box_id=package.box_id,
        created=package.created,
        expires=package.expires,
    )


@router.post(
    "/work-packages/{work_package_id}/files/{accession}/work-order-tokens",
    operation_id="create_download_work_order_token",
    tags=["WorkPackages", "download"],
    summary="Create a work order token for file download operations",
    description="Endpoint used to create a work order token for downloading a single file",
    responses={
        201: {
            "description": "Work order token has been created.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to create the work order token."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
@TRACER.start_as_current_span("routes.create_download_work_order_token")
async def create_download_work_order_token(
    work_package_id: UUID4,
    accession: str,
    repository: WorkPackageRepositoryDummy,
    work_package_access_token: WorkPackageAccessToken,
) -> JSONResponse:
    """Get an encrypted work order token using a work package access token."""
    try:
        if not (work_package_id and accession and work_package_access_token):
            raise repository.WorkPackageAccessError

        wot = await repository.get_download_wot(
            work_package_id=work_package_id,
            accession=accession,
            check_valid=True,
            work_package_access_token=work_package_access_token,
        )

        cache_control_header = {
            "Cache-Control": f"max-age={WORK_ORDER_TOKEN_VALID_SECONDS}, private"
        }
        return JSONResponse(content=wot, status_code=201, headers=cache_control_header)
    except repository.WorkPackageAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post(
    "/work-packages/{work_package_id}/boxes/{box_id}/work-order-tokens",
    operation_id="create_upload_work_order_token",
    tags=["WorkPackages", "upload"],
    summary="Create a work order token for file upload operations",
    description="Endpoint used to create a work order token for uploading a single file",
    responses={
        201: {
            "description": "Work order token has been created.",
        },
        403: {"description": "Not authorized to create the work order token."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
@TRACER.start_as_current_span("routes.create_upload_work_order_token")
async def create_upload_work_order_token(
    work_package_id: UUID4,
    box_id: UUID4,
    wot_request: UploadWorkOrderTokenRequest,
    repository: WorkPackageRepositoryDummy,
    work_package_access_token: WorkPackageAccessToken,
) -> JSONResponse:
    try:
        if not (
            work_package_id and box_id and wot_request and work_package_access_token
        ):
            raise repository.WorkPackageAccessError

        wot = await repository.get_upload_wot(
            work_package_id=work_package_id,
            box_id=box_id,
            work_type=wot_request.work_type,
            alias=wot_request.alias,
            file_id=wot_request.file_id,
            check_valid=True,
            work_package_access_token=work_package_access_token,
        )

        cache_control_header = {
            "Cache-Control": f"max-age={WORK_ORDER_TOKEN_VALID_SECONDS}, private"
        }
        return JSONResponse(content=wot, status_code=201, headers=cache_control_header)
    except repository.WorkPackageAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.get(
    "/users/{user_id}/datasets",
    operation_id="get_datasets",
    tags=["Datasets", "download"],
    summary="Get all datasets of the given user",
    description="Endpoint used to get details for all datasets"
    " that are accessible to the given user including their expiration dates.",
    responses={
        200: {
            "model": list[Dataset],
            "description": "Datasets have been fetched.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to get datasets."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("routes.get_datasets")
async def get_datasets(
    user_id: UUID4,
    repository: WorkPackageRepositoryDummy,
    auth_context: UserAuthContext,
) -> list[DatasetWithExpiration]:
    """Get datasets using an internal auth token with a user context."""
    try:
        if str(user_id) != auth_context.id:
            raise repository.WorkPackageAccessError("Not authorized to get datasets")
        datasets = await repository.get_datasets(user_id=user_id)
    except repository.WorkPackageAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return datasets


@router.get(
    "/users/{user_id}/boxes",
    operation_id="get_upload_boxes",
    tags=["UploadBoxes", "upload"],
    summary="Get all accessible upload boxes and access expiry for the given user",
    description="Endpoint used to get details for all upload boxes"
    + " that are accessible to the given user, along with the access expiration date.",
    responses={
        200: {
            "model": list[BoxWithExpiration],
            "description": "Upload boxes have been fetched.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to get upload boxes."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("routes.get_upload_boxes")
async def get_upload_boxes(
    user_id: UUID4,
    repository: WorkPackageRepositoryDummy,
    auth_context: UserAuthContext,
) -> list[BoxWithExpiration]:
    """Get upload boxes using an internal auth token with a user context."""
    try:
        if str(user_id) != auth_context.id:
            raise repository.WorkPackageAccessError(
                "Not authorized to get upload boxes"
            )
        boxes = await repository.get_upload_boxes(user_id=user_id)
    except repository.WorkPackageAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return boxes
