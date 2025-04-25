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
from typing import Annotated

from fastapi import APIRouter, Path, Response, status
from fastapi.exceptions import HTTPException
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError
from opentelemetry import trace

from auth_service.user_registry.deps import (
    IvaDaoDependency,
    UserDaoDependency,
)

from ..core.claims import (
    create_controlled_access_claim,
    dataset_id_for_download_access,
    has_download_access_for_dataset,
    is_valid_claim,
)
from ..core.utils import (
    iva_is_verified,
    user_exists,
    user_is_active,
    user_with_iva_exists,
)
from ..deps import ClaimDaoDependency
from ..models.claims import (
    Accession,
    Claim,
    ClaimCreation,
    ClaimUpdate,
    ClaimValidity,
    VisaType,
)

__all__ = ["router"]

log = logging.getLogger(__name__)
tracer = trace.get_tracer("auth_service.claims_repository")

router = APIRouter()


user_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The user was not found."
)
iva_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The IVA was not found."
)
claim_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The user claim was not found."
)


@router.post(
    "/users/{user_id}/claims",
    operation_id="post_claim",
    tags=["claims"],
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
@tracer.start_as_current_span("router.post_claim")
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


@router.get(
    "/users/{user_id}/claims",
    operation_id="get_claims",
    tags=["claims"],
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
@tracer.start_as_current_span("router.get_claims")
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


@router.patch(
    "/users/{user_id}/claims/{claim_id}",
    operation_id="patch_claim",
    tags=["claims"],
    summary="Revoke an existing user claim",
    description="Endpoint used to revoke a claim for a specified user.",
    responses={
        204: {"description": "User claim was successfully saved."},
        404: {"description": "The user claim was not found."},
        422: {"description": "Validation error in submitted user data."},
    },
    status_code=201,
)
@tracer.start_as_current_span("router.patch_user")
async def patch_user(
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


@router.delete(
    "/users/{user_id}/claims/{claim_id}",
    operation_id="delete_claim",
    tags=["claims"],
    summary="Delete an existing user claim",
    description="Endpoint used to delete an existing user claim.",
    responses={
        204: {"description": "User claim was successfully deleted."},
        404: {"description": "The user claim was not found."},
        422: {"description": "Validation error in submitted user or claim ID."},
    },
    status_code=201,
)
@tracer.start_as_current_span("router.delete_claim")
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


@router.post(
    "/download-access/users/{user_id}/ivas/{iva_id}/datasets/{dataset_id}",
    operation_id="grant_download_access",
    tags=["datasets"],
    summary="Grant download access permission for a dataset",
    description="Endpoint to add a controlled access grant for a given dataset"
    " so that it can be downloaded by the given user with the given IVA."
    " For internal use only.",
    responses={
        204: {"description": "Download access has been granted."},
        404: {"description": "The user or the IVA was not found."},
        422: {"description": "Validation error in submitted user IDs."},
    },
    status_code=204,
)
@tracer.start_as_current_span("router.grant_download_access")
async def grant_download_access(  # noqa: PLR0913
    validity: ClaimValidity,
    user_id: Annotated[
        str,
        Path(
            ...,
            alias="user_id",
            description="The internal ID of the user",
        ),
    ],
    iva_id: Annotated[
        str,
        Path(
            ...,
            alias="iva_id",
            description="The ID of the IVA",
        ),
    ],
    dataset_id: Annotated[
        Accession,
        Path(
            ...,
            alias="dataset_id",
            description="The ID of the dataset",
        ),
    ],
    user_dao: UserDaoDependency,
    iva_dao: IvaDaoDependency,
    claim_dao: ClaimDaoDependency,
    # internal service, authorization without token via service mesh
) -> Response:
    """Grant download access permission for a dataset to a user with the given IVA.

    Note that at this point the IVA needs to exist, but does not need to be verified.
    We check whether the user exists but we do not check whether the user is active.
    We also do not check here whether the dataset actually exists,
    but we check that the dataset_id looks like an accession.
    """
    if not await user_with_iva_exists(
        user_id, iva_id=iva_id, user_dao=user_dao, iva_dao=iva_dao
    ):
        raise iva_not_found_error

    claim = create_controlled_access_claim(
        user_id,
        iva_id,
        dataset_id,
        valid_from=validity.valid_from,
        valid_until=validity.valid_until,
    )
    await claim_dao.insert(claim)

    return Response(status_code=204)


@router.get(
    "/download-access/users/{user_id}/datasets/{dataset_id}",
    operation_id="check_download_access",
    tags=["datasets"],
    summary="Check download access permission for a dataset",
    description="Endpoint to check whether the given dataset"
    " can be downloaded by the given user. For internal use only.",
    responses={
        200: {"description": "Download access has been checked."},
        404: {"description": "The user was not found or is inactive."},
        422: {"description": "Validation error in submitted user IDs."},
    },
    status_code=200,
)
@tracer.start_as_current_span("router.check_download_access")
async def check_download_access(
    user_id: Annotated[
        str,
        Path(
            ...,
            alias="user_id",
            description="Internal ID of the user",
        ),
    ],
    dataset_id: Annotated[
        Accession,
        Path(
            ...,
            alias="dataset_id",
            description="Internal ID of the dataset",
        ),
    ],
    user_dao: UserDaoDependency,
    iva_dao: IvaDaoDependency,
    claim_dao: ClaimDaoDependency,
    # internal service, authorization without token via service mesh
) -> bool:
    """Check download access permission for a given dataset by a given user.

    Note that at this point we also check whether the corresponding IVA is verified
    and whether the user is currently active.
    However, we do not check here whether the dataset actually exists,
    only that the dataset_id looks like an accession.
    """
    if not await user_is_active(user_id, user_dao=user_dao):
        raise user_not_found_error

    # run through all controlled access grants for the user
    async for claim in claim_dao.find_all(
        mapping={
            "user_id": user_id,
            "visa_type": VisaType.CONTROLLED_ACCESS_GRANTS,
        }
    ):
        # check whether the claim is valid and for the right source
        if (
            is_valid_claim(claim)
            and claim.iva_id
            and has_download_access_for_dataset(claim, dataset_id)
            and await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
        ):
            return True

    return False


@router.get(
    "/download-access/users/{user_id}/datasets",
    operation_id="get_download_access_list",
    tags=["datasets"],
    summary="Get list of all dataset IDs with download access permission",
    description="Endpoint to get a list of the IDs of all datasets that"
    " can be downloaded by the given user. For internal use only.",
    responses={
        200: {
            "description": "Dataset IDs with download access have been retrieved.",
        },
        404: {"description": "The user was not found or is inactive."},
        422: {"description": "Validation error in submitted user IDs."},
    },
    status_code=200,
)
@tracer.start_as_current_span("router.get_datasets_with_download_access")
async def get_datasets_with_download_access(
    user_id: Annotated[
        str,
        Path(
            ...,
            alias="user_id",
            description="Internal ID of the user",
        ),
    ],
    user_dao: UserDaoDependency,
    iva_dao: IvaDaoDependency,
    claim_dao: ClaimDaoDependency,
    # internal service, authorization without token via service mesh
) -> list[str]:
    """Get list of all dataset IDs with download access permission for a given user.

    Note that at this point we also check whether the corresponding IVA is verified
    and whether the user is currently active.
    However, we do not check here whether the datasets actually exist.
    """
    if not await user_is_active(user_id, user_dao=user_dao):
        raise user_not_found_error

    # fetch all valid controlled access grants for the user
    dataset_ids = [
        dataset_id_for_download_access(claim)
        async for claim in claim_dao.find_all(
            mapping={
                "user_id": user_id,
                "visa_type": VisaType.CONTROLLED_ACCESS_GRANTS,
            }
        )
        if is_valid_claim(claim)
        and claim.iva_id
        and await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
    ]
    # filter out datasets from different sources and sort for reproducible output
    return sorted(dataset_id for dataset_id in dataset_ids if dataset_id)
