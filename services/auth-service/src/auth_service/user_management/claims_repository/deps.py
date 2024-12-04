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

"""FastAPI dependencies for the claims repository"""

from typing import Annotated

from auth_service.deps import (
    Depends,
    MongoDbDaoFactory,
    get_config,
    get_mongodb_dao_factory,
)

from .ports.dao import ClaimDao
from .translators.dao import ClaimDaoConfig, ClaimDaoFactory

__all__ = ["ClaimDao", "get_claim_dao"]


def get_claim_dao_factory(
    config: Annotated[ClaimDaoConfig, Depends(get_config)],
    dao_factory: Annotated[MongoDbDaoFactory, Depends(get_mongodb_dao_factory)],
) -> ClaimDaoFactory:
    """Get claim DAO factory."""
    return ClaimDaoFactory(config=config, dao_factory=dao_factory)


async def get_claim_dao(
    dao_factory: Annotated[ClaimDaoFactory, Depends(get_claim_dao_factory)],
) -> ClaimDao:
    """Get claim data access object."""
    return await dao_factory.get_claim_dao()
