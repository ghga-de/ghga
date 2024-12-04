# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from collections.abc import Callable

from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError

from auth_service.user_management.user_registry.deps import IvaDao, UserDao
from auth_service.user_management.user_registry.models.ivas import IvaState
from auth_service.user_management.user_registry.models.users import UserStatus

from ..deps import ClaimDao
from ..models.claims import VisaType
from .claims import is_data_steward_claim, is_valid_claim

__all__ = ["is_data_steward", "user_exists", "user_with_iva_exists"]


async def user_exists(user_id: str, *, user_dao: UserDao) -> bool:
    """Check whether the user with the given ID exists."""
    if not user_id:
        return False
    try:
        await user_dao.get_by_id(user_id)
    except ResourceNotFoundError:
        return False
    return True


async def user_is_active(user_id: str, *, user_dao: UserDao) -> bool:
    """Check whether the user with the given ID exists and is active."""
    if not user_id:
        return False
    try:
        user = await user_dao.get_by_id(user_id)
    except ResourceNotFoundError:
        return False
    return user.status == UserStatus.ACTIVE


async def user_with_iva_exists(
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


async def iva_is_verified(user_id: str, iva_id: str | None, *, iva_dao: IvaDao) -> bool:
    """Check that the specified IVA exists, belongs to the given user and is verified."""
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
    iva_dao: IvaDao,
    user_dao: UserDao | None = None,
    now: Callable[[], UTCDatetime] = now_as_utc,
):
    """Check whether the user with the given ID is an active data steward.

    If no User DAO is provided, the user is assumed to exist and be active.
    We also require that the data steward claim has a verified associated IVA.
    """
    if user_dao and not await user_is_active(user_id, user_dao=user_dao):
        return False
    async for claim in claim_dao.find_all(
        mapping={"user_id": user_id, "visa_type": VisaType.GHGA_ROLE}
    ):
        if (
            is_valid_claim(claim, now=now)
            and is_data_steward_claim(claim)
            and await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
        ):
            return True
    return False
