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

"""Functions to seed the claims repository with user claims."""

import logging

from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.correlation import set_new_correlation_id
from hexkit.protocols.dao import MultipleHitsFoundError, NoHitsFoundError

from auth_service.claims_repository.deps import ClaimDao
from auth_service.config import Config
from auth_service.user_registry.deps import IvaDao, UserDao
from auth_service.user_registry.models.ivas import Iva, IvaBasicData
from auth_service.user_registry.models.users import User, UserStatus

from ..models.claims import VisaType
from ..models.config import UserWithIVA
from .claims import Role, create_internal_role_claim
from .utils import get_role_from_claim

__all__ = ["seed_data_steward_claims"]

log = logging.getLogger(__name__)


async def _remove_existing_data_steward_claims(*, claim_dao: ClaimDao) -> None:
    """Remove all existing data steward claims"""
    num_removed_claims = 0
    async for claim in claim_dao.find_all(mapping={"visa_type": VisaType.GHGA_ROLE}):
        role = get_role_from_claim(claim)
        if role is Role.DATA_STEWARD:
            await claim_dao.delete(claim.id)
            num_removed_claims += 1
    log.info("Removed %d existing data steward claim(s).", num_removed_claims)


async def _add_user_with_ext_id(*, info: UserWithIVA, user_dao: UserDao) -> User:
    """Add a new user with the given external ID to the database."""
    user_dto = User(
        ext_id=info.ext_id,
        name=info.name,
        email=info.email,
        title=None,
        status=UserStatus.ACTIVE,
        registration_date=now_as_utc(),
    )
    await user_dao.insert(user_dto)
    return user_dto


def _check_data_steward_info(*, info: UserWithIVA, user: User) -> None:
    """Verify that the data steward has the given name and email address.

    This serves as a security check to ensure that the right user is configured.
    """
    if user.name != info.name:
        raise ValueError(
            f"Configured data steward with external ID {info.ext_id}"
            f" has the name '{user.name}', expected was '{info.name}'"
        )
    if user.email != info.email:
        raise ValueError(
            f"Configured data steward with external ID {info.ext_id}"
            f" has the email address <{user.email}>, expected was <{info.email}>"
        )


async def _add_iva_for_user(
    *, user_id: str, data: IvaBasicData, iva_dao: IvaDao
) -> Iva:
    """Add a new IVA for the given user with the given basic data."""
    now = now_as_utc()
    iva_dto = Iva(user_id=user_id, created=now, changed=now, **data.model_dump())
    await iva_dao.insert(iva_dto)
    return iva_dto


async def _add_configured_data_steward_claims(
    *,
    data_stewards: list[UserWithIVA],
    user_dao: UserDao,
    iva_dao: IvaDao,
    claim_dao: ClaimDao,
) -> None:
    # add configured data steward claims
    for data_steward in data_stewards:
        # add the data steward as a user
        ext_id = data_steward.ext_id
        try:
            user = await user_dao.find_one(mapping={"ext_id": ext_id})
        except MultipleHitsFoundError:
            log.error("External ID %r is not unique in the user registry.", ext_id)
            raise
        except NoHitsFoundError:
            try:
                user = await _add_user_with_ext_id(info=data_steward, user_dao=user_dao)
            except Exception as error:
                log.error(
                    "Could not add new user with external ID %r: %s", ext_id, error
                )
                raise
            log.warning("Added missing data steward with external ID %r.", ext_id)
        else:
            _check_data_steward_info(info=data_steward, user=user)
        # add the IVA of the data steward
        iva_data = IvaBasicData(
            type=data_steward.iva_type, value=data_steward.iva_value
        )
        try:
            iva = await iva_dao.find_one(
                mapping={
                    "user_id": user.id,
                    "type": iva_data.type,
                    "value": iva_data.value,
                }
            )
        except MultipleHitsFoundError:
            log.error(
                "IVA %s: %r is not unique for user with external ID %r.",
                iva_data.type,
                iva_data.value,
                ext_id,
            )
            raise
        except NoHitsFoundError:
            try:
                iva = await _add_iva_for_user(
                    user_id=user.id, data=iva_data, iva_dao=iva_dao
                )
            except Exception as error:
                log.error(
                    "Could not add new IVA for user with external ID %r: %s",
                    ext_id,
                    error,
                )
                raise
            log.warning(
                "Added missing IVA for data steward with external ID %r.", ext_id
            )
        # add the data steward claim for that user and that IVA
        claim = create_internal_role_claim(user.id, Role.DATA_STEWARD, iva.id)
        await claim_dao.insert(claim)
        log.info("Added data steward role for %r to the claims repository.", ext_id)


async def seed_data_steward_claims(
    *, config: Config, user_dao: UserDao, iva_dao: IvaDao, claim_dao: ClaimDao
) -> None:
    """Seed the claims repository with data steward claims.

    This function removes all existing data steward claims and then adds such
    claims for all data stewards specified via external user ID in the config.
    """
    if set(config.provide_apis).isdisjoint({"claims", "access"}):
        return
    data_stewards = config.add_as_data_stewards
    if not data_stewards:
        log.warning("No data stewards are defined in the configuration.")
    async with set_new_correlation_id():
        await _remove_existing_data_steward_claims(claim_dao=claim_dao)
        await _add_configured_data_steward_claims(
            data_stewards=data_stewards,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
        )
