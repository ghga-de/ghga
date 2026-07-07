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

"""Routes related to Upload Boxes"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4, NonNegativeInt

from rs.adapters.inbound.fastapi_ import dummies
from rs.adapters.inbound.fastapi_.auth import StewardAuthContext, UserAuthContext
from rs.adapters.inbound.fastapi_.http_exceptions import (
    HttpAccessionMapError,
    HttpArchivalPrereqsError,
    HttpBoxMaxSizeTooLowError,
    HttpBoxNotFoundError,
    HttpBoxStateError,
    HttpBoxTitleExistsError,
    HttpBoxVersionError,
    HttpIncompleteUploadsError,
    HttpInternalError,
    HttpNotAuthorizedError,
    HttpStateChangeError,
)
from rs.constants import TRACER
from rs.core.models import (
    AccessionMapRequest,
    BoxRetrievalResults,
    CreateUploadBoxRequest,
    FileUploadWithAccession,
    ResearchDataUploadBox,
    UpdateUploadBoxRequest,
    UploadBoxState,
)
from rs.ports.inbound.rdub_manager import RDUBManagerPort

log = logging.getLogger(__name__)

box_router = APIRouter()


@box_router.delete(
    "/{box_id}/uploads/{file_id}",
    summary="Delete file upload",
    description="Delete a file upload from an upload box. Requires Data Steward role"
    + " or upload access to the box.",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "File upload deleted successfully."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        404: {"description": "Upload box not found."},
        409: {"description": "File cannot be deleted while the box is locked."},
    },
)
@TRACER.start_as_current_span("routes.delete_file_upload")
async def delete_file_upload(
    box_id: UUID,
    file_id: UUID,
    registry: dummies.RegistryDummy,
    auth_context: UserAuthContext,
) -> None:
    """Delete a file upload from an upload box."""
    try:
        await registry.rdub_manager.delete_file_upload(
            box_id=box_id,
            file_id=file_id,
            auth_context=auth_context,
        )
    except RDUBManagerPort.BoxAccessError as err:
        raise HttpNotAuthorizedError() from err
    except RDUBManagerPort.BoxNotFoundError as err:
        raise HttpBoxNotFoundError(box_id=box_id) from err
    except RDUBManagerPort.BoxStateError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(message="Failed to delete file upload") from err


@box_router.delete(
    "/{box_id}",
    summary="Delete upload box",
    description="Delete a research data upload box and its files. Requires the Data"
    + " Steward role. The corresponding FileUploadBox and all file uploads are deleted"
    + " in the file box service; in-progress uploads are aborted and uploaded objects"
    + " are removed. Upload-access grants and accession mappings for the box are also"
    + " removed. Archived boxes cannot be deleted.",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Upload box deleted successfully."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        404: {"description": "Upload box not found."},
        409: {
            "description": "Deletion failed: outdated version or incompatible state."
        },
    },
)
@TRACER.start_as_current_span("routes.delete_research_data_upload_box")
async def delete_research_data_upload_box(
    box_id: UUID,
    registry: dummies.RegistryDummy,
    auth_context: StewardAuthContext,
    version: Annotated[
        int,
        Query(description="The expected current version of the upload box."),
    ],
) -> None:
    """Delete a research data upload box and its files. Requires Data Steward role."""
    try:
        await registry.rdub_manager.delete_research_data_upload_box(
            box_id=box_id,
            version=version,
            user_id=UUID(auth_context.id),
        )
    except RDUBManagerPort.BoxNotFoundError as err:
        raise HttpBoxNotFoundError(box_id=box_id) from err
    except RDUBManagerPort.BoxVersionError as err:
        raise HttpBoxVersionError() from err
    except RDUBManagerPort.BoxStateError as err:
        raise HttpBoxStateError(state=err.state) from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(message="Failed to delete upload box") from err


@box_router.patch(
    "/{box_id}",
    summary="Update upload box",
    description="Update modifiable details for a research data upload box, including"
    + " the description, title, and state. When modifying the state, users are only"
    + " allowed to move the state from OPEN to LOCKED, and all other changes are"
    + " restricted to Data Stewards. A note on archival: Once archived, the box may"
    + " no longer be modified, and files in the box will be moved to permanent storage."
    + " If any files in the box have yet to be re-encrypted, if the box is still open,"
    + " or if there are any files that lack an accession number, archival is denied.",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Upload box updated successfully."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        404: {"description": "Upload box not found."},
        409: {
            "description": (
                "Update failed due to a title conflict, an outdated request,"
                " or unmet prerequisites."
            )
        },
        422: {"description": "Validation error in request body."},
    },
)
@TRACER.start_as_current_span("routes.update_research_data_upload_box")
async def update_research_data_upload_box(
    box_id: UUID,
    request: UpdateUploadBoxRequest,
    registry: dummies.RegistryDummy,
    auth_context: UserAuthContext,
) -> None:
    """Update a ResearchDataUploadBox."""
    try:
        await registry.rdub_manager.update_research_data_upload_box(
            box_id=box_id,
            version=request.version,
            title=request.title,
            description=request.description,
            state=request.state,
            max_size=request.max_size,
            force=request.force,
            auth_context=auth_context,
        )
    except RDUBManagerPort.BoxAccessError as err:
        raise HttpNotAuthorizedError() from err
    except RDUBManagerPort.BoxNotFoundError as err:
        raise HttpBoxNotFoundError(box_id=box_id) from err
    except RDUBManagerPort.BoxTitleExistsError as err:
        raise HttpBoxTitleExistsError(title=request.title or "") from err
    except RDUBManagerPort.BoxVersionError as err:
        raise HttpBoxVersionError() from err
    except RDUBManagerPort.BoxIncompleteUploadsError as err:
        raise HttpIncompleteUploadsError(
            incomplete_uploads=err.incomplete_file_ids
        ) from err
    except RDUBManagerPort.ArchivalPrereqsError as err:
        raise HttpArchivalPrereqsError() from err
    except RDUBManagerPort.StateChangeError as err:
        raise HttpStateChangeError() from err
    except RDUBManagerPort.BoxMaxSizeTooLowError as err:
        raise HttpBoxMaxSizeTooLowError() from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(message="Failed to update upload box") from err


@box_router.get(
    "/{box_id}",
    summary="Get upload box details",
    description="Returns the details of an existing research data upload box.",
    response_model=ResearchDataUploadBox,
    responses={
        200: {
            "model": ResearchDataUploadBox,
            "description": "Upload box details successfully retrieved.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        404: {"description": "Upload box not found or access denied."},
    },
)
@TRACER.start_as_current_span("routes.get_research_data_upload_box")
async def get_research_data_upload_box(
    box_id: UUID,
    registry: dummies.RegistryDummy,
    auth_context: UserAuthContext,
) -> ResearchDataUploadBox:
    """Get details of a specific upload box. If the user doesn't have access to an
    existing box, this endpoint will return a 404.
    """
    try:
        return await registry.rdub_manager.get_research_data_upload_box(
            box_id=box_id, auth_context=auth_context
        )
    except RDUBManagerPort.BoxAccessError as err:
        # Return BoxAccessError as a 404 on purpose
        raise HttpBoxNotFoundError(box_id=box_id) from err
    except RDUBManagerPort.BoxNotFoundError as err:
        raise HttpBoxNotFoundError(box_id=box_id) from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(message="Failed to get upload box") from err


@box_router.get(
    "/{box_id}/uploads",
    summary="List files in upload box",
    description="List the details of all files uploads for a research data upload box.",
    response_model=list[FileUploadWithAccession],
    responses={
        200: {
            "model": list[FileUploadWithAccession],
            "description": "File upload information successfully retrieved.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        404: {"description": "Upload box not found."},
    },
)
@TRACER.start_as_current_span("routes.list_upload_box_files")
async def list_upload_box_files(
    box_id: UUID,
    registry: dummies.RegistryDummy,
    auth_context: UserAuthContext,
) -> list[FileUploadWithAccession]:
    """List file uploads in an upload box."""
    try:
        return await registry.rdub_manager.get_upload_box_files(
            box_id=box_id,
            auth_context=auth_context,
        )
    except RDUBManagerPort.BoxAccessError as err:
        raise HttpNotAuthorizedError() from err
    except RDUBManagerPort.BoxNotFoundError as err:
        raise HttpBoxNotFoundError(box_id=box_id) from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(message="Failed to list upload box files") from err


@box_router.post(
    "/{box_id}/file-ids",
    summary="Map file IDs to accession numbers for files in the upload box",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Accession map successfully submitted."},
        400: {
            "description": (
                "One or more duplicate, absent, or unknown file IDs detected."
            )
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        404: {"description": "Upload box not found."},
        409: {
            "description": (
                "The version of the requested box is out of date, or one or more"
                " accessions in the map already have mappings that conflict"
                " with the new request."
            )
        },
        422: {"description": "Validation error in request body."},
    },
)
@TRACER.start_as_current_span("routes.submit_accession_map")
async def submit_accession_map(
    box_id: UUID,
    request: AccessionMapRequest,
    registry: dummies.RegistryDummy,
    auth_context: StewardAuthContext,
) -> None:
    """Submit a file ID to accession number mapping for an upload box."""
    try:
        await registry.rdub_manager.store_accession_map(
            box_id=box_id,
            box_version=request.box_version,
            accession_map=request.mapping,
            study_id=request.study_id,
        )
    except RDUBManagerPort.AccessionMapError as err:
        raise HttpAccessionMapError(
            error_type=err.error_type,
            conflicting_accessions=err.conflicting_accessions,
            unknown_accessions=err.unknown_accessions,
            affected_file_ids=err.affected_file_ids,
            status_code=409
            if err.error_type in {"accession_conflict", "archived"}
            else 400,
        ) from err
    except RDUBManagerPort.BoxNotFoundError as err:
        raise HttpBoxNotFoundError(box_id=box_id) from err
    except RDUBManagerPort.BoxVersionError as err:
        raise HttpBoxVersionError() from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(message="Failed to update accession map") from err


@box_router.get(
    "",
    summary="List upload boxes",
    description=(
        "Returns a list of research data upload boxes. Results are sorted first by"
        + " locked status (unlocked followed by locked), then by most recently changed,"
        + " then by box ID. Data Stewards have access to all boxes, while regular users"
        + " may only access boxes to which they have been granted upload access."
    ),
    response_model=BoxRetrievalResults,
    responses={
        200: {
            "model": BoxRetrievalResults,
            "description": "Research data upload boxes successfully retrieved.",
        },
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        422: {"description": "Validation error in query parameters."},
    },
)
@TRACER.start_as_current_span("routes.get_research_data_upload_boxes")
async def get_research_data_upload_boxes(
    registry: dummies.RegistryDummy,
    auth_context: UserAuthContext,
    skip: Annotated[
        NonNegativeInt | None,
        Query(
            description="Number of research data upload boxes to skip for pagination",
        ),
    ] = None,
    limit: Annotated[
        NonNegativeInt | None,
        Query(
            description="Maximum number of research data upload boxes to return",
        ),
    ] = None,
    state: Annotated[
        UploadBoxState | None,
        Query(
            description="Filter by state. None returns all boxes.",
        ),
    ] = None,
) -> BoxRetrievalResults:
    """Get list of all research data upload boxes with pagination support.

    For data stewards, returns all boxes. For regular users, only returns boxes
    they have access to according to the access API.
    """
    try:
        return await registry.rdub_manager.get_research_data_upload_boxes(
            auth_context=auth_context,
            skip=skip,
            limit=limit,
            state=state,
        )
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(message="Failed to get upload boxes") from err


@box_router.post(
    "",
    summary="Create upload box",
    description="Create a new research data upload box to label and track related file"
    + " uploads for a given user.",
    response_model=UUID4,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": UUID4, "description": "Upload box created successfully."},
        401: {"description": "Not authenticated."},
        403: {"description": "Not authorized."},
        409: {"description": "A ResearchDataUploadBox with this title already exists."},
        422: {"description": "Validation error in request body."},
    },
)
@TRACER.start_as_current_span("routes.create_research_data_upload_box")
async def create_research_data_upload_box(
    request: CreateUploadBoxRequest,
    registry: dummies.RegistryDummy,
    auth_context: StewardAuthContext,
) -> UUID4:
    """Create a new upload box. Requires Data Steward role."""
    try:
        return await registry.rdub_manager.create_research_data_upload_box(
            title=request.title,
            description=request.description,
            storage_alias=request.storage_alias,
            max_size=request.max_size,
            data_steward_id=UUID(auth_context.id),
        )
    except RDUBManagerPort.BoxTitleExistsError as err:
        raise HttpBoxTitleExistsError(title=request.title) from err
    except Exception as err:
        log.error(err, exc_info=True)
        raise HttpInternalError(message="Failed to create upload box") from err
