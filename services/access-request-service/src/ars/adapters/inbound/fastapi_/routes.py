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
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response
from fastapi.exceptions import HTTPException
from pydantic import UUID4

from ars.adapters.inbound.fastapi_ import dummies
from ars.adapters.inbound.fastapi_.auth import StewardAuthContext, UserAuthContext
from ars.core.models import (
    AccessGrant,
    AccessRequest,
    AccessRequestCreationData,
    AccessRequestPatchData,
    AccessRequestStatus,
)

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="health",
    tags=["AccessRequests"],
    status_code=200,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.post(
    "/access-requests",
    operation_id="create_access_request",
    tags=["AccessRequests"],
    summary="Create an access request",
    description="Endpoint used to create a new access request",
    responses={
        201: {
            "model": str,
            "description": "Access request was successfully created",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to create an access request."},
        404: {"description": "Dataset not found"},
        422: {"description": "Validation error in submitted data."},
    },
    status_code=201,
)
async def create_access_request(
    creation_data: AccessRequestCreationData,
    repository: dummies.AccessRequestRepoDummy,
    auth_context: UserAuthContext,
) -> str:
    """Create an access request"""
    try:
        request = await repository.create(
            creation_data=creation_data, auth_context=auth_context
        )
    except repository.AccessRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except repository.DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except repository.AccessRequestInvalidDuration as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        log.error("Could not create access request: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Access request could not be created."
        ) from exc
    return str(request.id)


@router.get(
    "/access-requests",
    operation_id="get_access_requests",
    tags=["AccessRequests"],
    summary="Get access requests",
    description="Endpoint used to get existing access requests",
    responses={
        200: {
            "model": list[AccessRequest],
            "description": "Access requests have been fetched.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to get access requests."},
        422: {"description": "Validation error in submitted parameters."},
    },
    status_code=200,
)
async def get_access_requests(
    repository: dummies.AccessRequestRepoDummy,
    auth_context: UserAuthContext,
    user_id: Annotated[
        UUID4 | None,
        Query(
            ...,
            alias="user_id",
            description="The internal ID of the user",
        ),
    ] = None,
    dataset_id: Annotated[
        str | None,
        Query(
            ...,
            alias="dataset_id",
            description="The ID of the dataset",
        ),
    ] = None,
    status: Annotated[
        AccessRequestStatus | None,
        Query(
            ...,
            alias="status",
            description="The status of the access request",
        ),
    ] = None,
) -> list[AccessRequest]:
    """Get access requests"""
    try:
        return await repository.find_all(
            user_id=user_id,
            dataset_id=dataset_id,
            status=status,
            auth_context=auth_context,
        )
    except repository.AccessRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except repository.AccessRequestError as exc:
        log.error("Could not get access requests: %s", exc)
        raise HTTPException(
            status_code=500, detail="Access requests could not be fetched."
        ) from exc


@router.get(
    "/access-requests/{access_request_id}",
    operation_id="get_access_request",
    tags=["AccessRequests"],
    summary="Get access request",
    description="Endpoint used to get an existing access request",
    responses={
        200: {
            "model": AccessRequest,
            "description": "Access request has been fetched.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to get access request."},
        404: {"description": "Access request does not exist."},
        422: {"description": "Validation error in submitted data."},
    },
    status_code=200,
)
async def get_access_request(
    repository: dummies.AccessRequestRepoDummy,
    auth_context: UserAuthContext,
    access_request_id: Annotated[
        UUID4,
        Path(..., alias="access_request_id", description="ID of the access request"),
    ],
) -> AccessRequest:
    """Get access request"""
    try:
        return await repository.get(
            access_request_id=access_request_id,
            auth_context=auth_context,
        )
    except repository.AccessRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except repository.AccessRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        log.error("Could not get access request: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Access request could not be fetched."
        ) from exc


@router.patch(
    "/access-requests/{access_request_id}",
    operation_id="patch_access_request",
    tags=["AccessRequests"],
    summary="Set status or modify other fields of an access request",
    description="Endpoint used to set the status or modify other fields of an access request",
    responses={
        204: {"description": "Access request was successfully changed"},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to change access request."},
        404: {"description": "Access request does not exist."},
        422: {"description": "Validation error in submitted data."},
    },
    status_code=204,
)
async def patch_access_request(
    access_request_id: Annotated[
        UUID4,
        Path(..., alias="access_request_id", description="ID of the access request"),
    ],
    patch_data: AccessRequestPatchData,
    repository: dummies.AccessRequestRepoDummy,
    auth_context: StewardAuthContext,
) -> Response:
    """Set the status of an access request"""
    try:
        await repository.update(
            access_request_id,
            patch_data=patch_data,
            auth_context=auth_context,
        )
    except repository.AccessRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except repository.AccessRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (
        repository.AccessRequestClosed,
        repository.AccessRequestMissingIva,
        repository.AccessRequestInvalidDuration,
        repository.AccessRequestServerError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        log.error("Could not modify access request: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Access request could not be modified."
        ) from exc
    return Response(status_code=204)


@router.get(
    "/access-grants",
    operation_id="get_access_grants",
    tags=["AccessGrants"],
    summary="Get data access grants",
    description="Endpoint to get the list of all data access grants",
    responses={
        200: {
            "model": list[AccessGrant],
            "description": "Access grants have been fetched.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to get access grants."},
        422: {"description": "Validation error in submitted parameters."},
    },
    status_code=200,
)
async def get_access_grants(  # noqa: PLR0913
    repository: dummies.AccessRequestRepoDummy,
    auth_context: UserAuthContext,
    user_id: Annotated[
        UUID4 | None,
        Query(
            ...,
            alias="user_id",
            description="The internal ID of the user",
        ),
    ] = None,
    iva_id: Annotated[
        UUID4 | None,
        Query(
            ...,
            alias="iva_id",
            description="The ID of the IVA",
        ),
    ] = None,
    dataset_id: Annotated[
        str | None,
        Query(
            ...,
            alias="dataset_id",
            description="The ID of the dataset",
        ),
    ] = None,
    valid: Annotated[
        bool | None,
        Query(
            ...,
            alias="valid",
            description="Whether the grant is currently valid",
        ),
    ] = None,
) -> list[AccessGrant]:
    """Get data access grants.

    You can filter the grants by user ID, IVA ID, and dataset ID
    and by whether the grant is currently valid or not.
    """
    try:
        return await repository.get_grants(
            user_id=user_id,
            iva_id=iva_id,
            dataset_id=dataset_id,
            valid=valid,
            auth_context=auth_context,
        )
    except repository.AccessRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (repository.AccessGrantsError, repository.DatasetNotFoundError) as exc:
        log.error("Could not get data access grants: %s", exc)
        raise HTTPException(
            status_code=500, detail="Access requests could not be fetched."
        ) from exc


@router.delete(
    "/access-grants/{grant_id}",
    operation_id="revoke_access_grant",
    tags=["AccessGrants"],
    summary="Revoke a data access grant",
    description="Endpoint to revoke an existing data access grant.",
    responses={
        204: {
            "description": "The data access grant has been revoked.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized to revoke a data access grant."},
        404: {"description": "The data access grant was not found."},
        422: {"description": "Validation error in submitted data."},
    },
    status_code=204,
)
async def revoke_access_grant(
    grant_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="grant_id",
            description="The ID of the data access grant to revoke",
        ),
    ],
    repository: dummies.AccessRequestRepoDummy,
    auth_context: StewardAuthContext,
) -> Response:
    """Revoke an existing data access grant."""
    try:
        await repository.revoke_grant(grant_id, auth_context=auth_context)
    except repository.AccessRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except repository.AccessGrantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except repository.AccessGrantsError as exc:
        log.error("Could not revoke data access grant: %s", exc)
        raise HTTPException(
            status_code=500, detail="Data access grant could not be revoked."
        ) from exc

    return Response(status_code=204)
