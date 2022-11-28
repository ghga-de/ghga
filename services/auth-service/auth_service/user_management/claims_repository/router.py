# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"Routes for managing user claims"

import logging

from fastapi import APIRouter, Path, Response
from fastapi.exceptions import HTTPException
from ghga_service_chassis_lib.utils import now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError

from auth_service.user_management.user_registry.deps import UserDao, get_user_dao

from ..auth import AuthToken, RequireAuthToken
from .deps import ClaimDao, Depends, get_claim_dao
from .models.dto import Claim, ClaimCreation, ClaimFullCreation, ClaimUpdate
from .utils import user_exists

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter()


require_data_steward = Depends(RequireAuthToken(role="data_steward"))

user_not_found_error = HTTPException(status_code=404, detail="The user was not found.")
claim_not_found_error = HTTPException(
    status_code=404, detail="The user claim was not found."
)
own_claim_error = HTTPException(status_code=403, detail="Cannot modify own claims.")


@router.post(
    "/users/{user_id}/claims",
    operation_id="post_claim",
    tags=["claims"],
    summary="Store a user claim",
    description="Endpoint used to store a new claim about a user.",
    responses={
        201: {"model": Claim, "description": "Claim was successfully stored."},
        400: {"description": "Claim cannot be stored."},
        403: {"description": "Not authorized to create claims."},
        404: {"description": "The user was not found."},
        409: {"description": "Claim was already stored."},
        422: {"description": "Validation error in submitted ID or claims data."},
    },
    status_code=201,
)
async def post_claim(
    claim_creation: ClaimCreation,
    user_id: str = Path(
        ...,
        alias="user_id",
        title="Internal ID of the user",
    ),
    user_dao: UserDao = Depends(get_user_dao),
    claim_dao: ClaimDao = Depends(get_claim_dao),
    auth_token: AuthToken = require_data_steward,
) -> Claim:
    """Store a user claim"""
    if user_id == auth_token.id:
        raise own_claim_error

    if not await user_exists(user_id, user_dao):
        raise user_not_found_error

    current_date = now_as_utc()
    current_user_id = "someone"  # needs to be changed
    full_claim = ClaimFullCreation(
        **claim_creation.dict(),
        user_id=user_id,
        creation_date=current_date,
        creation_by=current_user_id,
        revocation_date=None,
        revocation_by=None
    )

    try:
        claim = await claim_dao.insert(full_claim)
    except Exception as error:
        log.error("Could not insert claim: %s", error)
        raise HTTPException(
            status_code=400, detail="User claim cannot be stored."
        ) from error
    return claim


@router.get(
    "/users/{user_id}/claims",
    operation_id="get_claims",
    tags=["claims"],
    summary="Get all claims for a given user",
    description="Endpoint used to get all claims for a specified user.",
    responses={
        200: {"model": list[Claim], "description": "User claims have been retrieved."},
        401: {"description": "Not authorized to get user claims."},
        403: {"description": "Not authorized to request claims."},
        404: {"description": "The user was not found."},
        422: {"description": "Validation error in submitted user ID."},
    },
    status_code=200,
)
async def get_claims(
    user_id: str = Path(
        ...,
        alias="user_id",
        title="Internal ID of the user",
    ),
    user_dao: UserDao = Depends(get_user_dao),
    claim_dao: ClaimDao = Depends(get_claim_dao),
    _auth_token: AuthToken = require_data_steward,
) -> list[Claim]:
    """Get all claims for a given user"""
    if not await user_exists(user_id, user_dao):
        raise user_not_found_error

    return [claim async for claim in claim_dao.find_all(mapping={"user_id": user_id})]


# pylint: disable=too-many-arguments
@router.patch(
    "/users/{user_id}/claims/{claim_id}",
    operation_id="patch_claim",
    tags=["claims"],
    summary="Revoke an existing user claim",
    description="Endpoint used to revoke a claim for a specified user.",
    responses={
        204: {"description": "User claim was successfully saved."},
        403: {"description": "Not authorized to modify claims."},
        404: {"description": "The user claim was not found."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
async def patch_user(
    claim_update: ClaimUpdate,
    user_id: str = Path(
        ...,
        alias="user_id",
        title="Internal user ID",
    ),
    claim_id: str = Path(
        ...,
        alias="claim_id",
        title="Internal claim ID",
    ),
    user_dao: UserDao = Depends(get_user_dao),
    claim_dao: ClaimDao = Depends(get_claim_dao),
    auth_token: AuthToken = require_data_steward,
) -> Response:
    """Revoke an existing user claim"""
    if user_id == auth_token.id:
        raise own_claim_error

    if not await user_exists(user_id, user_dao):
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

    current_user_id = "someone"  # needs to be changed

    claim = claim.copy(
        update={"revocation_date": revocation_date, "revocation_by": current_user_id}
    )
    try:
        await claim_dao.update(claim)
    except ResourceNotFoundError as error:
        raise claim_not_found_error from error

    return Response(status_code=204)


@router.delete(
    "/users/{user_id}/claims/{claim_id}",
    operation_id="delete_claim",
    tags=["claims"],
    summary="Delete an existing user claim",
    description="Endpoint used to delete an existing user claim.",
    responses={
        204: {"description": "User claim was successfully deleted."},
        403: {"description": "Not authorized to delete claims."},
        404: {"description": "The user claim was not found."},
        422: {"description": "Validation error in submitted user or claim ID."},
    },
    status_code=201,
)
async def delete_claim(
    user_id: str = Path(
        ...,
        alias="user_id",
        title="Internal user ID",
    ),
    claim_id: str = Path(
        ...,
        alias="claim_id",
        title="Internal claim ID",
    ),
    user_dao: UserDao = Depends(get_user_dao),
    claim_dao: ClaimDao = Depends(get_claim_dao),
    auth_token: AuthToken = require_data_steward,
) -> Response:
    """Delete an existing user claim"""
    if user_id == auth_token.id:
        raise own_claim_error

    if not await user_exists(user_id, user_dao):
        raise user_not_found_error

    try:
        claim = await claim_dao.get_by_id(claim_id)
    except ResourceNotFoundError as error:
        raise claim_not_found_error from error

    if claim.user_id != user_id:
        raise claim_not_found_error

    try:
        await claim_dao.delete(id_=claim_id)
    except ResourceNotFoundError as error:
        raise claim_not_found_error from error

    return Response(status_code=204)
