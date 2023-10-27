# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from wps.adapters.inbound.fastapi_.auth import (
    RequiresAuthContext,
    RequiresWorkPackageAccessToken,
)
from wps.adapters.inbound.fastapi_.dummies import WorkPackageRepositoryDummy
from wps.core.models import (
    Dataset,
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
        403: {"description": "Not authorized to create a work package."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
async def create_work_package(
    creation_data: WorkPackageCreationData,
    repository: WorkPackageRepositoryDummy,
    auth_context: RequiresAuthContext,
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
        403: {"description": "Not authorized to get the work package."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=200,
)
async def get_work_package(
    work_package_id: str,
    repository: WorkPackageRepositoryDummy,
    work_package_access_token: RequiresWorkPackageAccessToken,
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
        created=package.created,
        expires=package.expires,
    )


@router.post(
    "/work-packages/{work_package_id}/files/{file_id}/work-order-tokens",
    operation_id="create_work_order_token",
    tags=["WorkPackages"],
    summary="Create a work order token",
    description="Endpoint used to create a work order token",
    responses={
        201: {
            "description": "Work order token has been created.",
        },
        403: {"description": "Not authorized to create the work order token."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
async def create_work_order_token(
    work_package_id: str,
    file_id: str,
    repository: WorkPackageRepositoryDummy,
    work_package_access_token: RequiresWorkPackageAccessToken,
) -> str:
    """Get an encrypted work order token using a work package access token."""
    try:
        if not (work_package_id and file_id and work_package_access_token):
            raise repository.WorkPackageAccessError
        return await repository.work_order_token(
            work_package_id=work_package_id,
            file_id=file_id,
            check_valid=True,
            work_package_access_token=work_package_access_token,
        )
    except repository.WorkPackageAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.get(
    "/users/{user_id}/datasets",
    operation_id="get_datasets",
    tags=["Datasets"],
    summary="Get all datasets of the given user",
    description="Endpoint used to get details for all datasets"
    " that are accessible to the given user",
    responses={
        200: {
            "model": list[Dataset],
            "description": "Datasets have been fetched.",
        },
        403: {"description": "Not authorized to get datasets."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=200,
)
async def get_datasets(
    user_id: str,
    repository: WorkPackageRepositoryDummy,
    auth_context: RequiresAuthContext,
) -> list[Dataset]:
    """Get datasets using an internal auth token with a user context."""
    try:
        if user_id != auth_context.id:
            raise repository.WorkPackageAccessError("Not authorized to get datasets")
        datasets = await repository.get_datasets(auth_context=auth_context)
    except repository.WorkPackageAccessError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return datasets
