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

"""Functions to seed the repository with user claims."""

import logging

from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import MultipleHitsFoundError, NoHitsFoundError

from auth_service.config import Config
from auth_service.deps import get_mongo_kafka_dao_factory, get_mongodb_dao_factory
from auth_service.user_management.claims_repository.core.claims import (
    create_data_steward_claim,
)
from auth_service.user_management.claims_repository.core.utils import (
    is_data_steward_claim,
)
from auth_service.user_management.claims_repository.deps import (
    ClaimDao,
    get_claim_dao,
    get_claim_dao_factory,
)
from auth_service.user_management.claims_repository.models.claims import VisaType
from auth_service.user_management.user_registry.deps import (
    UserDao,
    get_user_dao,
    get_user_dao_factory,
)
from auth_service.user_management.user_registry.models.users import (
    User,
    UserStatus,
)

__all__ = ["seed_data_steward_claims"]

log = logging.getLogger(__name__)


async def _remove_existing_data_steward_claims(claim_dao: ClaimDao) -> None:
    """Remove all existing data steward claims"""
    num_removed_claims = 0
    async for claim in claim_dao.find_all(mapping={"visa_type": VisaType.GHGA_ROLE}):
        if is_data_steward_claim(claim):
            await claim_dao.delete(claim.id)
            num_removed_claims += 1
    log.info("Removed %d existing data steward claim(s).", num_removed_claims)


async def _add_user_with_ext_id(user: str | dict, user_dao: UserDao) -> User:
    """Add a new user with the given external ID to the database."""
    if not isinstance(user, dict):
        raise TypeError("User data (name and email) is missing.")
    user_dto = User(
        ext_id=user["ext_id"],
        name=user["name"],
        email=user["email"],
        title=None,
        status=UserStatus.ACTIVE,
        registration_date=now_as_utc(),
    )
    await user_dao.insert(user_dto)
    return user_dto


async def _add_configured_data_steward_claims(
    data_stewards: list[str | dict], user_dao: UserDao, claim_dao: ClaimDao
) -> None:
    # add configured data steward claims
    for data_steward in data_stewards:
        ext_id = (
            data_steward.get("ext_id")
            if isinstance(data_steward, dict)
            else data_steward
        )
        if not ext_id:
            log.warning("External ID of data steward is missing: %r.", data_steward)
            continue
        try:
            user = await user_dao.find_one(mapping={"ext_id": ext_id})
        except MultipleHitsFoundError:
            log.warning("External ID %r is not unique in the user registry.", ext_id)
            continue
        except NoHitsFoundError:
            try:
                user = await _add_user_with_ext_id(data_steward, user_dao=user_dao)
            except Exception as error:
                log.warning(
                    "Could not add new user with external ID %r: %s", ext_id, error
                )
                continue
            else:
                log.warning("Added missing data steward with external ID %r.", ext_id)
        claim = create_data_steward_claim(user.id)
        await claim_dao.insert(claim)
        log.info("Added data steward role for %r to the claims repository.", ext_id)


async def seed_data_steward_claims(config: Config) -> None:
    """Seed the claims repository with data steward claims.

    This function removes all existing data steward claims and then adds such
    claims for all data stewards specified via external user ID in the config.
    """
    if "claims" not in config.include_apis:
        return
    data_stewards = config.add_as_data_stewards
    if not data_stewards:
        log.warning("No data stewards are defined in the configuration.")
        return
    async for dao_publisher_factory in get_mongo_kafka_dao_factory(config=config):
        user_dao = await get_user_dao(
            dao_factory=get_user_dao_factory(
                config=config,
                dao_publisher_factory=dao_publisher_factory,
            )
        )
        claim_dao = await get_claim_dao(
            dao_factory=get_claim_dao_factory(
                config=config,
                dao_factory=get_mongodb_dao_factory(config=config),
            )
        )
        await _remove_existing_data_steward_claims(claim_dao=claim_dao)
        await _add_configured_data_steward_claims(
            data_stewards, user_dao=user_dao, claim_dao=claim_dao
        )
