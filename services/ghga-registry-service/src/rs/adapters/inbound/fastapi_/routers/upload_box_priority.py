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
from rs.adapters.inbound.fastapi_.http_exceptions import HttpInternalError
from rs.constants import TRACER
from rs.core.models import (
    UpdateUploadBoxPriorityRequest,
    UploadBoxPriorityResponse,
    UploadBoxPrioritySaveResult,
)
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


@priority_router.patch(
    "",
    summary="Move boxes in the upload box priority list",
    description="Applies the moves to the stored list in order. A move puts a box"
    + " directly before another box, or at the end if `before` is null. A move is"
    + " skipped if `before` is not in the list or is the moved box itself, and the"
    + " moves after it still apply. Boxes that are archived or no longer exist are"
    + " dropped after the last move. `version` does not have to match the stored"
    + " version; it only sets `includes_other_changes`. Requires the Data Steward"
    + " role.",
    response_model=UploadBoxPrioritySaveResult,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Moves saved."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        422: {"description": "Validation error in request body."},
        500: {
            "description": (
                "The list kept changing during the save, or another error occurred."
            )
        },
    },
)
@TRACER.start_as_current_span("routes.update_upload_box_priority")
async def update_upload_box_priority(
    request: UpdateUploadBoxPriorityRequest,
    registry: dummies.RegistryDummy,
    auth_context: StewardAuthContext,
) -> UploadBoxPrioritySaveResult:
    """Move boxes in the upload box priority list.

    Requires Data Steward role.
    """
    try:
        return await registry.priority_manager.move_boxes(
            version=request.version,
            moves=request.moves,
            user_id=UUID(auth_context.id),
        )
    except UploadBoxPriorityManagerPort.PriorityUpdateError as err:
        log.error(err)
        raise HttpInternalError(
            message="The upload box priority list kept changing, please try again"
        ) from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(
            message="Failed to save the upload box priority list"
        ) from err
