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

from fastapi import APIRouter, status

from rs.adapters.inbound.fastapi_ import dummies, http_exceptions
from rs.adapters.inbound.fastapi_.http_authorization import (
    require_map_file_ids_work_order,
)
from rs.adapters.inbound.fastapi_.rest_models import (
    PID,
    FileIdMappingRequest,
    MapFileIdsWorkOrder,
)
from rs.constants import TRACER

files_router = APIRouter(tags=["files"])

log = logging.getLogger(__name__)


@files_router.post(
    "/file-ids/{study_pid}",
    summary="Post file ID mappings",
    operation_id="postFilenames",
    status_code=status.HTTP_204_NO_CONTENT,
)
@TRACER.start_as_current_span("files_router.post_file_ids")
async def post_file_ids(
    study_pid: PID,
    body: FileIdMappingRequest,
    file_controller: dummies.FileControllerDummy,
    work_order: Annotated[MapFileIdsWorkOrder, require_map_file_ids_work_order],
):
    """Store file accession to internal file ID mappings."""
    if work_order.study_pid != study_pid:
        raise http_exceptions.HttpNotAuthorizedError()

    log.info(
        "Received file ID mapping (file accession to internal file ID) request"
        + " from user ID %s for study PID %s.",
        work_order.user_id,
        work_order.study_pid,
    )

    try:
        await file_controller.post_file_ids(
            study_pid=study_pid, file_id_map=body.mapping
        )
    # TODO: Full error handling once full service logic is added
    except Exception as err:
        log.exception("Unexpected error in post_file_ids")
        raise http_exceptions.HttpInternalError() from err
