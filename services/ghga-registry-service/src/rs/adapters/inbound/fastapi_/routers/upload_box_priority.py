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

"""Routes related to the Upload Box Priority list"""

import logging
from uuid import UUID

from fastapi import APIRouter, status

from rs.adapters.inbound.fastapi_ import dummies
from rs.adapters.inbound.fastapi_.auth import StewardAuthContext
from rs.adapters.inbound.fastapi_.http_exceptions import (
    HttpBoxVersionError,
    HttpInternalError,
)
from rs.constants import TRACER
from rs.core.models import UpdateUploadBoxPriorityRequest, UploadBoxPriorityResponse
from rs.ports.inbound.priority import UploadBoxPriorityManagerPort

log = logging.getLogger(__name__)

priority_router = APIRouter()


@priority_router.get(
    "",
    summary="Get the upload box priority list",
    description="Returns the order in which the files of the upload boxes are"
    + " re-encrypted. If no list is stored yet, the version is 0 and the other fields"
    + " are empty. Requires the Data Steward role.",
    response_model=UploadBoxPriorityResponse,
    responses={
        200: {"description": "Upload box priority list successfully retrieved."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
    },
)
@TRACER.start_as_current_span("routes.get_upload_box_priority")
async def get_upload_box_priority(
    registry: dummies.RegistryDummy,
    auth_context: StewardAuthContext,
) -> UploadBoxPriorityResponse:
    """Get the upload box priority list.

    Requires Data Steward role.
    """
    try:
        return await registry.priority_manager.get_priority()
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(
            message="Failed to get the upload box priority list"
        ) from err


@priority_router.put(
    "",
    summary="Set the order of the upload box priority list",
    description="Replaces the order of the stored list with `box_ids`, which must hold"
    + " every research data upload box that is not archived, once. `version` must be"
    + " the stored version, or 0 if no list is stored yet. Returns the stored list"
    + " after the save. Requires the Data Steward role.",
    response_model=UploadBoxPriorityResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Order saved."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        409: {
            "description": (
                "The list changed since `version`, or holds other boxes than"
                + " `box_ids`."
            )
        },
        422: {"description": "Validation error in request body."},
        500: {"description": "Internal error."},
    },
)
@TRACER.start_as_current_span("routes.set_upload_box_priority")
async def set_upload_box_priority(
    request: UpdateUploadBoxPriorityRequest,
    registry: dummies.RegistryDummy,
    auth_context: StewardAuthContext,
) -> UploadBoxPriorityResponse:
    """Set the order of the upload box priority list.

    Requires Data Steward role.
    """
    try:
        return await registry.priority_manager.set_order(
            version=request.version,
            box_ids=request.box_ids,
            user_id=UUID(auth_context.id),
        )
    except UploadBoxPriorityManagerPort.PriorityChangedError as err:
        raise HttpBoxVersionError() from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(
            message="Failed to save the upload box priority list"
        ) from err
