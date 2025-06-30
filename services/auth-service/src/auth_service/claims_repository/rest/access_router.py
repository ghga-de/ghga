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
from typing import Annotated

from fastapi import APIRouter, Path, Response, status
from fastapi.exceptions import HTTPException
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.opentelemetry import start_span

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
from ..core.utils import iva_is_verified, user_is_active, user_with_iva_exists
from ..deps import ClaimDaoDependency
from ..models.claims import Accession, ClaimValidity, VisaType

__all__ = ["router"]

log = logging.getLogger(__name__)

router = APIRouter()


user_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The user was not found."
)
iva_not_found_error = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="The IVA was not found."
)

TAGS: list[str | Enum] = ["access"]


@start_span()
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


@start_span()
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
    async for claim in claim_dao.find_all(
        mapping={
            "user_id": user_id,
            "visa_type": VisaType.CONTROLLED_ACCESS_GRANTS,
        }
    ):
        # check whether the claim is valid and for the right source
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


@start_span()
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
    # run through all controlled access grants for the user
    async for claim in claim_dao.find_all(
        mapping={
            "user_id": user_id,
            "visa_type": VisaType.CONTROLLED_ACCESS_GRANTS,
        }
    ):
        # consider only valid controlled access grants for the user
        if not (
            is_valid_claim(claim)
            and claim.iva_id
            and await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
        ):
            continue
        # consider only those for the right source
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
