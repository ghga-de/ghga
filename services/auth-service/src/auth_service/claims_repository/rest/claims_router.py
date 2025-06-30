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
#

"""Routes for managing user claims"""

import logging
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Path, Response, status
from fastapi.exceptions import HTTPException
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.opentelemetry import start_span
from hexkit.protocols.dao import ResourceNotFoundError

from auth_service.user_registry.deps import UserDaoDependency

from ..core.utils import user_exists
from ..deps import ClaimDaoDependency
from ..models.claims import Claim, ClaimCreation, ClaimUpdate

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter()


user_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The user was not found."
)
claim_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The user claim was not found."
)

TAGS: list[str | Enum] = ["claims"]


@start_span()
@router.post(
    "/users/{user_id}/claims",
    operation_id="post_claim",
    tags=TAGS,
    summary="Store a user claim",
    description="Endpoint used to store a new claim about a user.",
    responses={
        201: {"model": Claim, "description": "Claim was successfully stored."},
        400: {"description": "Claim cannot be stored."},
        404: {"description": "The user was not found."},
        409: {"description": "Claim was already stored."},
        422: {"description": "Validation error in submitted ID or claims data."},
    },
    status_code=201,
)
async def post_claim(
    claim_creation: ClaimCreation,
    user_id: Annotated[
        str,
        Path(
            ...,
            alias="user_id",
            description="Internal ID of the user",
        ),
    ],
    user_dao: UserDaoDependency,
    claim_dao: ClaimDaoDependency,
) -> Claim:
    """Store a user claim"""
    if not await user_exists(user_id, user_dao=user_dao):
        raise user_not_found_error

    current_date = now_as_utc()
    full_claim = Claim(
        **claim_creation.model_dump(),
        user_id=user_id,
        creation_date=current_date,
        revocation_date=None,
    )

    try:
        await claim_dao.insert(full_claim)
    except Exception as error:
        log.error("Could not insert claim: %s", error)
        raise HTTPException(
            status_code=400, detail="User claim cannot be stored."
        ) from error
    return full_claim


@start_span()
@router.get(
    "/users/{user_id}/claims",
    operation_id="get_claims",
    tags=TAGS,
    summary="Get all claims for a given user",
    description="Endpoint used to get all claims for a specified user.",
    responses={
        200: {"model": list[Claim], "description": "User claims have been retrieved."},
        401: {"description": "Not authorized to get user claims."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user ID."},
    },
    status_code=200,
)
async def get_claims(
    user_id: Annotated[
        str,
        Path(
            ...,
            alias="user_id",
            description="Internal ID of the user",
        ),
    ],
    user_dao: UserDaoDependency,
    claim_dao: ClaimDaoDependency,
) -> list[Claim]:
    """Get all claims for a given user"""
    if not await user_exists(user_id, user_dao=user_dao):
        raise user_not_found_error

    return [claim async for claim in claim_dao.find_all(mapping={"user_id": user_id})]


@start_span()
@router.patch(
    "/users/{user_id}/claims/{claim_id}",
    operation_id="patch_claim",
    tags=TAGS,
    summary="Revoke an existing user claim",
    description="Endpoint used to revoke a claim for a specified user.",
    responses={
        204: {"description": "User claim was successfully saved."},
        404: {"description": "The user claim was not found."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
async def patch_claim(
    claim_update: ClaimUpdate,
    user_id: Annotated[
        str,
        Path(
            ...,
            alias="user_id",
            description="Internal user ID",
        ),
    ],
    claim_id: Annotated[
        str,
        Path(
            ...,
            alias="claim_id",
            description="Internal claim ID",
        ),
    ],
    user_dao: UserDaoDependency,
    claim_dao: ClaimDaoDependency,
) -> Response:
    """Revoke an existing user claim"""
    if not await user_exists(user_id, user_dao=user_dao):
        raise user_not_found_error

    try:
        claim = await claim_dao.get_by_id(claim_id)
    except ResourceNotFoundError as error:
        raise claim_not_found_error from error

    if claim.user_id != user_id:
        raise claim_not_found_error

    revocation_date = claim_update.revocation_date  # is not null per validation
    if claim.revocation_date and revocation_date > claim.revocation_date:
        raise HTTPException(status_code=422, detail="Already revoked earlier.")

    claim = claim.model_copy(update={"revocation_date": revocation_date})
    try:
        await claim_dao.update(claim)
    except ResourceNotFoundError as error:
        raise claim_not_found_error from error

    return Response(status_code=204)


@start_span()
@router.delete(
    "/users/{user_id}/claims/{claim_id}",
    operation_id="delete_claim",
    tags=TAGS,
    summary="Delete an existing user claim",
    description="Endpoint used to delete an existing user claim.",
    responses={
        204: {"description": "User claim was successfully deleted."},
        404: {"description": "The user claim was not found."},
        422: {"description": "Validation error in submitted user or claim ID."},
    },
    status_code=201,
)
async def delete_claim(
    user_id: Annotated[
        str,
        Path(
            ...,
            alias="user_id",
            description="Internal user ID",
        ),
    ],
    claim_id: Annotated[
        str,
        Path(
            ...,
            alias="claim_id",
            description="Internal claim ID",
        ),
    ],
    user_dao: UserDaoDependency,
    claim_dao: ClaimDaoDependency,
) -> Response:
    """Delete an existing user claim"""
    if not await user_exists(user_id, user_dao=user_dao):
        raise user_not_found_error

    try:
        claim = await claim_dao.get_by_id(claim_id)
    except ResourceNotFoundError as error:
        raise claim_not_found_error from error

    if claim.user_id != user_id:
        raise claim_not_found_error

    try:
        await claim_dao.delete(claim_id)
    except ResourceNotFoundError as error:
        raise claim_not_found_error from error

    return Response(status_code=204)
