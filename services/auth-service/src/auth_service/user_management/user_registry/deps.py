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

"""FastAPI dependencies for the user registry"""

from auth_service.deps import (
    Depends,
    MongoDbDaoFactory,
    get_config,
    get_mongodb_dao_factory,
)

from .core.registry import UserRegistry, UserRegistryConfig
from .ports.dao import IvaDao, UserDao
from .ports.registry import UserRegistryPort
from .translators.dao import UserDaoConfig, UserDaoFactory

__all__ = ["get_user_dao", "IvaDao", "UserDao"]


def get_user_dao_factory(
    config: UserDaoConfig = Depends(get_config),
    dao_factory: MongoDbDaoFactory = Depends(get_mongodb_dao_factory),
) -> UserDaoFactory:
    """Get user DAO factory."""
    return UserDaoFactory(config=config, dao_factory=dao_factory)


async def get_user_dao(
    dao_factory: UserDaoFactory = Depends(get_user_dao_factory),
) -> UserDao:
    """Get user data access object."""
    return await dao_factory.get_user_dao()


async def get_iva_dao(
    dao_factory: UserDaoFactory = Depends(get_user_dao_factory),
) -> IvaDao:
    """Get IVA data access object."""
    return await dao_factory.get_iva_dao()


async def get_user_registry(
    config: UserRegistryConfig = Depends(get_config),
    dao_factory: UserDaoFactory = Depends(get_user_dao_factory),
) -> UserRegistryPort:
    """Get user registry."""
    return UserRegistry(
        config=config,
        user_dao=await dao_factory.get_user_dao(),
        iva_dao=await dao_factory.get_iva_dao(),
    )
