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
"""FastAPI routes for S3 upload metadata ingest"""

import logging
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import UUID4

from fis.adapters.inbound.fastapi_ import dummies
from fis.adapters.inbound.fastapi_.http_authorization import JWT, require_data_hub_jwt
from fis.constants import TRACER
from fis.core import models
from fis.ports.inbound.interrogation import InterrogationHandlerPort

log = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    summary="health",
    tags=["FileIngestService"],
    status_code=200,
)
@TRACER.start_as_current_span("routes.health")
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.get(
    "/storages/{storage_alias}/uploads",
    summary="Serve a list of new file uploads (yet to be interrogated)",
    operation_id="listUploads",
    tags=["FileIngestService"],
    status_code=status.HTTP_200_OK,
)
@TRACER.start_as_current_span("routes.list_uploads")
async def list_uploads(
    storage_alias: str,
    interrogator: dummies.InterrogatorPort,
    _token: Annotated[JWT, require_data_hub_jwt],
) -> list[models.BaseFileInformation]:
    """Return a list of not-yet-interrogated files for a Data Hub (storage_alias)"""
    try:
        return await interrogator.get_files_not_yet_interrogated(
            storage_alias=storage_alias
        )
    except Exception as err:
        error = HTTPException(status_code=500, detail="Something went wrong.")
        log.error(error, exc_info=True)
        raise error from err


@router.post(
    "/storages/{storage_alias}/uploads/can_remove",
    summary="Returns a list of IDs indicating which objects can be removed from the interrogation bucket",
    operation_id="getRemovableFiles",
    tags=["FileIngestService"],
    status_code=status.HTTP_200_OK,
)
@TRACER.start_as_current_span("routes.get_removable_files")
async def get_removable_files(
    storage_alias: str,
    interrogator: dummies.InterrogatorPort,
    _token: Annotated[JWT, require_data_hub_jwt],
    object_ids: list[UUID4] = Body(),
) -> list[UUID4]:
    """Returns a subset of the provided object ID list containing the IDs of all S3
    objects which may be now removed from the interrogation bucket.
    """
    try:
        return [
            o for o in object_ids if await interrogator.check_if_removable(object_id=o)
        ]
    except Exception as err:
        error = HTTPException(status_code=500, detail="Something went wrong.")
        log.error(error, exc_info=True)
        raise error from err


@router.post(
    "/storages/{storage_alias}/interrogation-reports",
    summary="Accepts an InterrogationReport for a file",
    operation_id="postInterrogationReport",
    tags=["FileIngestService"],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such file exists"},
        status.HTTP_409_CONFLICT: {"description": "Report conflicts with database"},
    },
)
@TRACER.start_as_current_span("routes.post_interrogation_report")
async def post_interrogation_report(
    storage_alias: str,
    interrogator: dummies.InterrogatorPort,
    _token: Annotated[JWT, require_data_hub_jwt],
    report: models.InterrogationReportWithSecret = Body(),
) -> None:
    """Post an InterrogationReport"""
    try:
        await interrogator.handle_interrogation_report(report=report)
    except InterrogationHandlerPort.FileNotFoundError as err:
        raise HTTPException(
            status_code=404, detail=f"File {report.file_id} not found."
        ) from err
    except InterrogationHandlerPort.InterrogationReportConflict as err:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Already received an InterrogationReport for file {report.file_id}"
                + " and this one does not match."
            ),
        ) from err
    except Exception as err:
        error = HTTPException(status_code=500, detail="Something went wrong.")
        log.error(error, exc_info=True, extra={"file_id": report.file_id})
        raise error from err
