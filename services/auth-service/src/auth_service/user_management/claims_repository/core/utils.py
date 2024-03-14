# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Core utilities for the Claims Repository."""

from typing import Callable, Optional

from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError

from auth_service.user_management.user_registry.deps import IvaDao, UserDao
from auth_service.user_management.user_registry.models.ivas import IvaState

from ..deps import ClaimDao
from ..models.claims import VisaType
from .claims import is_data_steward_claim, is_valid_claim

__all__ = ["user_exists", "iva_exists", "is_data_steward"]


async def user_exists(user_id: str, *, user_dao: UserDao) -> bool:
    """Check whether the user with the given ID exists."""
    if not user_id:
        return False
    try:
        await user_dao.get_by_id(user_id)
    except ResourceNotFoundError:
        return False
    return True


async def iva_exists(
    user_id: str, iva_id: str, *, user_dao: UserDao, iva_dao: IvaDao
) -> bool:
    """Check whether the specified user exists and has the specified IVA.

    The IVA must exist and belong to the user, but does not need to be verified.
    """
    if not user_id or not iva_id:
        return False
    try:
        await user_dao.get_by_id(user_id)
        iva = await iva_dao.get_by_id(iva_id)
    except ResourceNotFoundError:
        return False
    return iva.user_id == user_id


async def iva_is_verified(user_id: str, iva_id: str, *, iva_dao: IvaDao) -> bool:
    """Check that the specied IVA exists, belongs to the given user and is verified."""
    if not user_id or not iva_id:
        return False
    try:
        iva = await iva_dao.get_by_id(iva_id)
    except ResourceNotFoundError:
        return False
    return iva.user_id == user_id and iva.state == IvaState.VERIFIED


async def is_data_steward(
    user_id: str,
    *,
    claim_dao: ClaimDao,
    user_dao: Optional[UserDao] = None,
    now: Callable[[], UTCDatetime] = now_as_utc,
):
    """Check whether the user with the given ID is a data steward.

    If no User DAO is provided, the user is assumed to exist.
    """
    if user_dao and not await user_exists(user_id, user_dao=user_dao):
        return False
    async for claim in claim_dao.find_all(
        mapping={"user_id": user_id, "visa_type": VisaType.GHGA_ROLE}
    ):
        if is_valid_claim(claim, now=now) and is_data_steward_claim(claim):
            return True
    return False
