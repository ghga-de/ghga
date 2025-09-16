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

"""Routes for managing user access to datasets"""

import logging
from enum import Enum
from operator import attrgetter
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response, status
from fastapi.exceptions import HTTPException
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.protocols.dao import NoHitsFoundError, ResourceNotFoundError
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from auth_service.constants import TRACER
from auth_service.user_registry.deps import (
    IvaDaoDependency,
    UserDaoDependency,
)

from ...user_registry.models.users import User
from ..core.claims import (
    box_id_for_upload_access,
    create_controlled_access_claim,
    create_controlled_access_filter,
    create_upload_access_claim,
    create_upload_access_filter,
    dataset_id_for_download_access,
    has_download_access_for_dataset,
    has_upload_access_for_box,
    is_valid_claim,
)
from ..core.utils import iva_is_verified, user_is_active, user_with_iva_exists
from ..deps import ClaimDaoDependency
from ..models.claims import Accession, ClaimValidity, DownloadGrant, UploadGrant

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter()


download_grant_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="The download access grant was not found.",
)
user_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The user was not found."
)
iva_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The IVA was not found."
)

TAGS: list[str | Enum] = ["access"]


# Download Access Endpoints


@router.get(
    "/download-access/grants",
    operation_id="get_download_access_grants",
    tags=TAGS,
    summary="Get download access grants",
    description="Endpoint to get the list of all download access grants. Can be filtered by user ID, IVA ID, and dataset ID.",
    responses={
        200: {
            "model": list[DownloadGrant],
            "description": "Access grants have been fetched.",
        },
    },
    status_code=200,
)
@TRACER.start_as_current_span("access_router.get_download_access_grants")
async def get_download_access_grants(  # noqa: PLR0913
    claim_dao: ClaimDaoDependency,
    user_dao: UserDaoDependency,
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
    # internal service, authorization without token via service mesh
) -> list[DownloadGrant]:
    """Get download access grants.

    You can filter the grants by user ID, IVA ID, and dataset ID
    and by whether the grant is currently valid or not.
    """
    # Determine all controlled access grants for the user
    grants: list[DownloadGrant] = []
    users: dict[UUID, User | None] = {}  # user cache

    mapping = create_controlled_access_filter(
        user_id=user_id, iva_id=iva_id, dataset_id=dataset_id
    )
    async for claim in claim_dao.find_all(mapping=mapping):
        if claim.revocation_date:
            continue  # revoked claims should be considered deleted as grants
        if valid is not None and is_valid_claim(claim) != valid:
            continue  # filter by validity if requested
        dataset_id = dataset_id_for_download_access(claim)
        if not dataset_id:
            continue  # consider only claims for datasets
        # find user name and email
        _user_id = claim.user_id
        try:
            user = users[_user_id]
        except KeyError:
            try:
                user = await user_dao.get_by_id(_user_id)
            except ResourceNotFoundError:
                user = None
            users[_user_id] = user
        if not user:
            continue
        grants.append(
            DownloadGrant(
                id=claim.id,
                user_id=_user_id,
                iva_id=claim.iva_id,
                dataset_id=dataset_id,
                created=claim.creation_date,
                valid_from=claim.valid_from,
                valid_until=claim.valid_until,
                user_name=user.name,
                user_email=user.email,
                user_title=user.title,
            )
        )
    # sort the output by ID to make it reproducible
    return sorted(grants, key=attrgetter("id"))


@router.delete(
    "/download-access/grants/{grant_id}",
    operation_id="revoke_download_access_grant",
    tags=TAGS,
    summary="Revoke a download access grant",
    description="Endpoint to revoke an existing download access grant.",
    responses={
        204: {
            "description": "Access grant has been revoked.",
        },
        404: {"description": "The access grant was not found."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("access_router.revoke_download_access_grant")
async def revoke_download_access_grant(
    grant_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="grant_id",
            description="The ID of the grant to revoke",
        ),
    ],
    claim_dao: ClaimDaoDependency,
    # internal service, authorization without token via service mesh
) -> Response:
    """Revoke a download access grants."""
    mapping = cast(dict[str, str | UUID4 | None], create_controlled_access_filter())
    mapping.update({"id": grant_id, "revocation_date": None})
    try:
        claim = await claim_dao.find_one(mapping=mapping)
    except NoHitsFoundError as error:
        raise download_grant_not_found_error from error

    claim = claim.model_copy(update={"revocation_date": now_utc_ms_prec()})
    try:
        await claim_dao.update(claim)
    except ResourceNotFoundError as error:
        raise download_grant_not_found_error from error

    return Response(status_code=204)


@router.post(
    "/download-access/users/{user_id}/ivas/{iva_id}/datasets/{dataset_id}",
    operation_id="grant_download_access",
    tags=TAGS,
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
@TRACER.start_as_current_span("access_router.grant_download_access")
async def grant_download_access(  # noqa: PLR0913
    validity: ClaimValidity,
    user_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="user_id",
            description="The internal ID of the user",
        ),
    ],
    iva_id: Annotated[
        UUID4,
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
    tags=TAGS,
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
@TRACER.start_as_current_span("access_router.check_download_access")
async def check_download_access(
    user_id: Annotated[
        UUID4,
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
) -> UTCDatetime | None:
    """Check download access permission for a given dataset by a given user.

    Returns the date until which the user has access to the dataset or null if
    the user currently does not have access to the dataset.

    Note that at this point we also check whether the corresponding IVA is verified
    and whether the user is currently active.
    However, we do not check here whether the dataset actually exists,
    only that the dataset_id looks like an accession.
    """
    if not await user_is_active(user_id, user_dao=user_dao):
        raise user_not_found_error

    valid_until: UTCDatetime | None = None
    # run through all controlled access grants for the user
    mapping = create_controlled_access_filter(user_id=user_id)
    async for claim in claim_dao.find_all(mapping=mapping):
        # check whether the claim is valid and for a dataset
        if not (
            is_valid_claim(claim)
            and claim.iva_id
            and has_download_access_for_dataset(claim, dataset_id)
            and await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
        ):
            continue
        if valid_until and valid_until >= claim.valid_until:
            # we already found a claim with longer validity
            continue
        # memorize the date until which the user has access
        valid_until = claim.valid_until

    return valid_until


@router.get(
    "/download-access/users/{user_id}/datasets",
    operation_id="get_download_access_list",
    tags=TAGS,
    summary="Get list of all dataset IDs with download access permission",
    description="Endpoint to get the IDs of all datasets that can be downloaded"
    " by the given user mapped to until when the dataset can be requested."
    " For internal use only.",
    responses={
        200: {
            "description": "Dataset IDs with download access have been retrieved.",
        },
        404: {"description": "The user was not found or is inactive."},
        422: {"description": "Validation error in submitted user IDs."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("access_router.get_datasets_with_download_access")
async def get_datasets_with_download_access(
    user_id: Annotated[
        UUID4,
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
) -> dict[str, UTCDatetime]:
    """Get all dataset IDs with download access permission for a given user.

    Returns a mapping of dataset IDs to the date until which the user has access.

    Note that at this point we also check whether the corresponding IVA is verified
    and whether the user is currently active.
    However, we do not check here whether the datasets actually exist.
    """
    if not await user_is_active(user_id, user_dao=user_dao):
        raise user_not_found_error

    dataset_id_to_end_date: dict[str, UTCDatetime] = {}
    mapping = create_controlled_access_filter(user_id=user_id)
    # run through all controlled access grants for the user
    async for claim in claim_dao.find_all(mapping=mapping):
        # consider only valid controlled access grants for the user
        if not (
            is_valid_claim(claim)
            and claim.iva_id
            and await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
        ):
            continue
        # consider only claims for a dataset
        dataset_id = dataset_id_for_download_access(claim)
        if not dataset_id:
            continue
        valid_until = dataset_id_to_end_date.get(dataset_id)
        if valid_until and valid_until >= claim.valid_until:
            # we already found a claim with longer validity
            continue
        # map the dataset ID to the date until which the user has access
        dataset_id_to_end_date[dataset_id] = claim.valid_until

    # sort the output by dataset ID to make it reproducible
    return dict(sorted(dataset_id_to_end_date.items()))


# Upload Access Endpoints


upload_grant_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="The upload access grant was not found.",
)


@router.get(
    "/upload-access/grants",
    operation_id="get_upload_access_grants",
    tags=TAGS,
    summary="Get upload access grants",
    description="Endpoint to get the list of all upload access grants. Can be filtered by user ID, IVA ID, and box ID.",
    responses={
        200: {
            "model": list[UploadGrant],
            "description": "Upload access grants have been fetched.",
        },
    },
    status_code=200,
)
@TRACER.start_as_current_span("access_router.get_upload_access_grants")
async def get_upload_access_grants(  # noqa: PLR0913
    claim_dao: ClaimDaoDependency,
    user_dao: UserDaoDependency,
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
    box_id: Annotated[
        UUID4 | None,
        Query(
            ...,
            alias="box_id",
            description="The ID of the research data upload box",
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
    # internal service, authorization without token via service mesh
) -> list[UploadGrant]:
    """Get upload access grants.

    You can filter the grants by user ID, IVA ID, and box ID
    and by whether the grant is currently valid or not.
    """
    # Determine all upload access grants for the user
    grants: list[UploadGrant] = []
    users: dict[UUID, User | None] = {}  # user cache

    mapping = create_upload_access_filter(user_id=user_id, iva_id=iva_id, box_id=box_id)
    async for claim in claim_dao.find_all(mapping=mapping):
        if claim.revocation_date:
            continue  # revoked claims should be considered deleted as grants
        if valid is not None and is_valid_claim(claim) != valid:
            continue  # filter by validity if requested
        box_id = box_id_for_upload_access(claim)
        if not box_id:
            continue  # consider only claims for upload boxes
        # find user name and email
        _user_id = claim.user_id
        try:
            user = users[_user_id]
        except KeyError:
            try:
                user = await user_dao.get_by_id(_user_id)
            except ResourceNotFoundError:
                user = None
            users[_user_id] = user
        if not user:
            continue
        grants.append(
            UploadGrant(
                id=claim.id,
                user_id=_user_id,
                iva_id=claim.iva_id,
                box_id=box_id,
                created=claim.creation_date,
                valid_from=claim.valid_from,
                valid_until=claim.valid_until,
                user_name=user.name,
                user_email=user.email,
                user_title=user.title,
            )
        )
    # sort the output by ID to make it reproducible
    return sorted(grants, key=attrgetter("id"))


@router.delete(
    "/upload-access/grants/{grant_id}",
    operation_id="revoke_upload_access_grant",
    tags=TAGS,
    summary="Revoke an upload access grant",
    description="Endpoint to revoke an existing upload access grant.",
    responses={
        204: {
            "description": "Upload access grant has been revoked.",
        },
        404: {"description": "The upload access grant was not found."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("access_router.revoke_upload_access_grant")
async def revoke_upload_access_grant(
    grant_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="grant_id",
            description="The ID of the grant to revoke",
        ),
    ],
    claim_dao: ClaimDaoDependency,
    # internal service, authorization without token via service mesh
) -> Response:
    """Revoke an upload access grant."""
    mapping = cast(dict[str, str | UUID4 | None], create_upload_access_filter())
    mapping.update({"id": grant_id, "revocation_date": None})
    try:
        claim = await claim_dao.find_one(mapping=mapping)
    except NoHitsFoundError as error:
        raise upload_grant_not_found_error from error

    claim = claim.model_copy(update={"revocation_date": now_utc_ms_prec()})
    try:
        await claim_dao.update(claim)
    except ResourceNotFoundError as error:
        raise upload_grant_not_found_error from error

    return Response(status_code=204)


@router.post(
    "/upload-access/users/{user_id}/ivas/{iva_id}/boxes/{box_id}",
    operation_id="grant_upload_access",
    tags=TAGS,
    summary="Grant upload access permission for a box",
    description="Endpoint to add an upload access grant for a given box"
    " so that it can be used for upload by the given user with the given IVA."
    " For internal use only.",
    responses={
        204: {"description": "Upload access has been granted."},
        404: {"description": "The user or the IVA was not found."},
        422: {"description": "Validation error in submitted user IDs."},
    },
    status_code=204,
)
@TRACER.start_as_current_span("access_router.grant_upload_access")
async def grant_upload_access(  # noqa: PLR0913
    validity: ClaimValidity,
    user_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="user_id",
            description="The internal ID of the user",
        ),
    ],
    iva_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="iva_id",
            description="The ID of the IVA",
        ),
    ],
    box_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="box_id",
            description="The ID of the research data upload box",
        ),
    ],
    user_dao: UserDaoDependency,
    iva_dao: IvaDaoDependency,
    claim_dao: ClaimDaoDependency,
    # internal service, authorization without token via service mesh
) -> Response:
    """Grant upload access permission for an upload box to a user with the given IVA.

    Note that at this point the IVA needs to exist, but does not need to be verified.
    We check whether the user exists but we do not check whether the user is active.
    We also do not check here whether the upload box actually exists.
    """
    if not await user_with_iva_exists(
        user_id, iva_id=iva_id, user_dao=user_dao, iva_dao=iva_dao
    ):
        raise iva_not_found_error

    claim = create_upload_access_claim(
        user_id,
        iva_id,
        box_id,
        valid_from=validity.valid_from,
        valid_until=validity.valid_until,
    )
    await claim_dao.insert(claim)

    return Response(status_code=204)


@router.get(
    "/upload-access/users/{user_id}/boxes/{box_id}",
    operation_id="check_upload_access",
    tags=TAGS,
    summary="Check upload access permission for a box",
    description="Endpoint to check whether the given upload box"
    " can be used for upload by the given user. For internal use only.",
    responses={
        200: {"description": "Upload access has been checked."},
        404: {"description": "The user was not found or is inactive."},
        422: {"description": "Validation error in submitted user IDs."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("access_router.check_upload_access")
async def check_upload_access(
    user_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="user_id",
            description="Internal ID of the user",
        ),
    ],
    box_id: Annotated[
        UUID4,
        Path(
            ...,
            alias="box_id",
            description="Internal ID of the research data upload box",
        ),
    ],
    user_dao: UserDaoDependency,
    iva_dao: IvaDaoDependency,
    claim_dao: ClaimDaoDependency,
    # internal service, authorization without token via service mesh
) -> UTCDatetime | None:
    """Check upload access permission for a given upload box by a given user.

    Returns the date until which the user has access to the upload box or null if
    the user currently does not have access to the upload box.

    Note that at this point we also check whether the corresponding IVA is verified
    and whether the user is currently active.
    However, we do not check here whether the upload box actually exists.
    """
    if not await user_is_active(user_id, user_dao=user_dao):
        raise user_not_found_error

    valid_until: UTCDatetime | None = None
    # run through all upload access grants for the user
    mapping = create_upload_access_filter(user_id=user_id)
    async for claim in claim_dao.find_all(mapping=mapping):
        # check whether the claim is valid and for an upload box
        if not (
            is_valid_claim(claim)
            and claim.iva_id
            and has_upload_access_for_box(claim, box_id)
            and await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
        ):
            continue
        if valid_until and valid_until >= claim.valid_until:
            # we already found a claim with longer validity
            continue
        # memorize the date until which the user has access
        valid_until = claim.valid_until

    return valid_until


@router.get(
    "/upload-access/users/{user_id}/boxes",
    operation_id="get_upload_access_list",
    tags=TAGS,
    summary="Get list of all upload box IDs with upload access permission",
    description="Endpoint to get the IDs of all upload boxes that can be used for"
    " upload by the given user mapped to until when the box can be accessed."
    " For internal use only.",
    responses={
        200: {
            "description": "Upload box IDs with upload access have been retrieved.",
        },
        404: {"description": "The user was not found or is inactive."},
        422: {"description": "Validation error in submitted user IDs."},
    },
    status_code=200,
)
@TRACER.start_as_current_span("access_router.get_boxes_with_upload_access")
async def get_boxes_with_upload_access(
    user_id: Annotated[
        UUID4,
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
) -> dict[UUID4, UTCDatetime]:
    """Get all upload box IDs with upload access permission for a given user.

    Returns a mapping of upload box IDs to the date until which the user has access.

    Note that at this point we also check whether the corresponding IVA is verified
    and whether the user is currently active.
    However, we do not check here whether the upload boxes actually exist.
    """
    if not await user_is_active(user_id, user_dao=user_dao):
        raise user_not_found_error

    box_id_to_end_date: dict[UUID4, UTCDatetime] = {}
    mapping = create_upload_access_filter(user_id=user_id)
    # run through all upload access grants for the user
    async for claim in claim_dao.find_all(mapping=mapping):
        # consider only valid upload access grants for the user
        if not (
            is_valid_claim(claim)
            and claim.iva_id
            and await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
        ):
            continue
        # consider only claims for an upload box
        box_id = box_id_for_upload_access(claim)
        if not box_id:
            continue
        valid_until = box_id_to_end_date.get(box_id)
        if valid_until and valid_until >= claim.valid_until:
            # we already found a claim with longer validity
            continue
        # map the upload box ID to the date until which the user has access
        box_id_to_end_date[box_id] = claim.valid_until

    # sort the output by upload box ID to make it reproducible
    return dict(sorted(box_id_to_end_date.items()))
