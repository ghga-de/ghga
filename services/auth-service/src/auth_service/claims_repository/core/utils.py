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

"""Core utilities for the Claims Repository."""

from collections import defaultdict
from collections.abc import Callable

from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError
from pydantic import UUID4

from auth_service.user_registry.deps import IvaDao, UserDao
from auth_service.user_registry.models.ivas import IvaState
from auth_service.user_registry.models.users import User, UserStatus, UserWithRoles

from ..deps import ClaimDao
from ..models.claims import VisaType
from .claims import get_role_from_claim, is_valid_claim

__all__ = [
    "get_active_roles",
    "iva_is_verified",
    "user_exists",
    "user_is_active",
    "user_with_iva_exists",
    "with_added_roles",
]


async def user_exists(user_id: UUID4, *, user_dao: UserDao) -> bool:
    """Check whether the user with the given ID exists."""
    if not user_id:
        return False
    try:
        await user_dao.get_by_id(user_id)
    except ResourceNotFoundError:
        return False
    return True


async def user_is_active(user_id: UUID4, *, user_dao: UserDao) -> bool:
    """Check whether the user with the given ID exists and is active."""
    if not user_id:
        return False
    try:
        user = await user_dao.get_by_id(user_id)
    except ResourceNotFoundError:
        return False
    return user.status == UserStatus.ACTIVE


async def user_with_iva_exists(
    user_id: UUID4, iva_id: UUID4, *, user_dao: UserDao, iva_dao: IvaDao
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


async def iva_is_verified(
    user_id: UUID4, iva_id: UUID4 | None, *, iva_dao: IvaDao
) -> bool:
    """Check that the specified IVA exists, belongs to the given user and is verified."""
    if not user_id or not iva_id:
        return False
    try:
        iva = await iva_dao.get_by_id(iva_id)
    except ResourceNotFoundError:
        return False
    return iva.user_id == user_id and iva.state == IvaState.VERIFIED


async def get_active_roles(
    user_id: UUID4,
    *,
    claim_dao: ClaimDao,
    iva_dao: IvaDao | None = None,
    user_dao: UserDao | None = None,
    now: Callable[[], UTCDatetime] = now_as_utc,
) -> list[str]:
    """Get the active roles of the user with the given ID.

    If no User DAO is provided, the user is assumed to exist and be active,
    otherwise we check this as a requirement for having any active roles.

    If no IVA DAO is provided, the corresponding IVAs are ignored, otherwise
    for a role to be considered active, we require that the corresponding
    claim has a verified associated IVA.
    """
    if user_dao and not await user_is_active(user_id, user_dao=user_dao):
        return []
    roles = set()
    async for claim in claim_dao.find_all(
        mapping={"user_id": user_id, "visa_type": VisaType.GHGA_ROLE}
    ):
        if is_valid_claim(claim, now=now):
            role = get_role_from_claim(claim)
            if role and (
                not iva_dao
                or await iva_is_verified(user_id, claim.iva_id, iva_dao=iva_dao)
            ):
                roles.add(str(role))
    return sorted(roles)


async def with_added_roles(
    users: list[User],
    *,
    claim_dao: ClaimDao,
    now: Callable[[], UTCDatetime] = now_as_utc,
) -> list[UserWithRoles]:
    """Return the given list of users with their roles added."""
    user_ids: list[UUID4] = [user.id for user in users]
    roles: dict[UUID4, set] = defaultdict(set)
    # Note: Here we rely on "$in" being supported by the DAO.
    async for claim in claim_dao.find_all(
        mapping={"user_id": {"$in": user_ids}, "visa_type": VisaType.GHGA_ROLE}
    ):
        if is_valid_claim(claim, now=now) and (role := get_role_from_claim(claim)):
            roles[claim.user_id].add(str(role))
    return [
        UserWithRoles(
            **user.model_dump(),
            roles=sorted(roles[user.id]),
        )
        for user in users
    ]
