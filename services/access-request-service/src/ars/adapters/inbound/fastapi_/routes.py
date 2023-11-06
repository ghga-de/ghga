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
from typing import Optional

from fastapi import APIRouter, Response
from fastapi.exceptions import HTTPException

from ars.adapters.inbound.fastapi_ import dummies
from ars.adapters.inbound.fastapi_.auth import (
    AuthContext,
    require_steward_context,
    require_user_context,
)
from ars.core.models import (
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
        403: {"description": "Not authorized to create an access request."},
        422: {"description": "Validation error in submitted data."},
    },
    status_code=201,
)
async def create_access_request(
    creation_data: AccessRequestCreationData,
    repository: dummies.AccessRequestRepoDummy,
    auth_context: AuthContext = require_user_context,
) -> str:
    """Create an access request"""
    try:
        request = await repository.create(
            creation_data=creation_data, auth_context=auth_context
        )
    except repository.AccessRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except repository.AccessRequestInvalidDuration as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        log.error("Could not create access request: %s", exc)
        raise HTTPException(
            status_code=500, detail="Access request could not be created."
        ) from exc
    return request.id


@router.get(
    "/access-requests",
    operation_id="get_access_request",
    tags=["AccessRequests"],
    summary="Get access requests",
    description="Endpoint used to get existing access requests",
    responses={
        200: {
            "model": list[AccessRequest],
            "description": "Access requests have been fetched.",
        },
        403: {"description": "Not authorized to get access requests."},
        422: {"description": "Validation error in submitted parameters."},
    },
    status_code=200,
)
async def get_access_requests(
    repository: dummies.AccessRequestRepoDummy,
    dataset_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[AccessRequestStatus] = None,
    auth_context: AuthContext = require_user_context,
) -> list[AccessRequest]:
    """Get access requests"""
    try:
        requests = await repository.get(
            user_id=user_id,
            dataset_id=dataset_id,
            status=status,
            auth_context=auth_context,
        )
    except repository.AccessRequestError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        log.error("Could not get access requests: %s", exc)
        raise HTTPException(
            status_code=500, detail="Access requests could not be fetched."
        ) from exc
    return requests


@router.patch(
    "/access-requests/{access_request_id}",
    operation_id="patch_access_request",
    tags=["AccessRequests"],
    summary="Set status of an access request",
    description="Endpoint used to set the status of an access request",
    responses={
        204: {"description": "Status was successfully changed"},
        403: {"description": "Not authorized to create an access request."},
        404: {"description": "Access request does not exist."},
        422: {"description": "Validation error in submitted data."},
    },
    status_code=204,
)
async def patch_access_request(
    access_request_id: str,
    patch_data: AccessRequestPatchData,
    repository: dummies.AccessRequestRepoDummy,
    auth_context: AuthContext = require_steward_context,
) -> Response:
    """Set the status of an access request"""
    status = patch_data.status
    try:
        await repository.update(
            access_request_id, status=status, auth_context=auth_context
        )
    except repository.AccessRequestAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except repository.AccessRequestNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except repository.AccessRequestInvalidState as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        log.error("Could not modify access request: %s", exc)
        raise HTTPException(
            status_code=500, detail="Access request could not be modified."
        ) from exc
    return Response(status_code=204)
