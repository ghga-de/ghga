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


"""
Module containing the main FastAPI router and all route functions.
"""

import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Path, status

from wps.adapters.inbound.fastapi_.auth import (
    AuthContext,
    requires_auth_context,
    requires_work_package_access_token,
)
from wps.container import Container
from wps.core.models import (
    WorkPackageCreationData,
    WorkPackageCreationResponse,
    WorkPackageDetails,
)
from wps.ports.inbound.repository import WorkPackageRepositoryPort

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
@inject
async def create_work_package(
    creation_data: WorkPackageCreationData,
    repository: WorkPackageRepositoryPort = Depends(
        Provide[Container.work_package_repository]
    ),
    auth_context: AuthContext = requires_auth_context,
) -> WorkPackageCreationResponse:
    """Create a work package using an internal auth token with a user context."""
    return await repository.create(creation_data, auth_context=auth_context)


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
@inject
async def get_work_package(
    work_package_id: str = Path(
        ...,
        alias="work_package_id",
    ),
    repository: WorkPackageRepositoryPort = Depends(
        Provide[Container.work_package_repository]
    ),
    work_package_access_token: str = requires_work_package_access_token,
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
        raise HTTPException(
            status_code=403, detail="Not authorized to get the work package."
        ) from error
    return WorkPackageDetails(
        type=package.type,
        file_ids=package.file_ids,
        file_extensions=package.file_extensions,
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
@inject
async def create_work_order_token(
    work_package_id: str = Path(
        ...,
        alias="work_package_id",
    ),
    file_id: str = Path(
        ...,
        alias="file_id",
    ),
    repository: WorkPackageRepositoryPort = Depends(
        Provide[Container.work_package_repository]
    ),
    work_package_access_token: str = requires_work_package_access_token,
) -> str:
    """Get an excrypted work order token using a work package access token."""
    try:
        if not (work_package_id and file_id and work_package_access_token):
            raise repository.WorkPackageAccessError
        return await repository.work_order_token(
            work_package_id,
            file_id,
            check_valid=True,
            work_package_access_token=work_package_access_token,
        )
    except repository.WorkPackageAccessError as error:
        raise HTTPException(
            status_code=403, detail="Not authorized to create the work order token."
        ) from error
