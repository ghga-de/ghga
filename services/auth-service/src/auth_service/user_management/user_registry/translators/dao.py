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

"""Translation between general and user specific DAOs."""

from hexkit.protocols.dao import DaoFactoryProtocol
from pydantic import Field
from pydantic_settings import BaseSettings

from ..models.ivas import Iva as IvaDto
from ..models.ivas import IvaFullData as IvaCreationDto
from ..models.users import User as UserDto
from ..models.users import UserData as UserCreationDto
from ..ports.dao import IvaDao, UserDao, UserDaoFactoryPort

__all__ = ["UserDaoFactory", "UserDaoConfig"]


class UserDaoConfig(BaseSettings):
    """User DAO config parameters and their defaults."""

    users_collection: str = Field(
        default="users", description="Name of the collection for users"
    )
    user_tokens_collection: str = Field(
        default="user_tokens", description="Name of the collection for user tokens"
    )
    ivas_collection: str = Field(
        default="ivas", description="Name of the collection for IVAs"
    )


class UserDaoFactory(UserDaoFactoryPort):
    """Translation between UserDaoFactoryPort and DaoFactoryProtocol."""

    def __init__(
        self, *, config: UserDaoConfig, dao_factory: DaoFactoryProtocol
    ) -> None:
        """Configure with provider for the DaoFactoryProtocol"""
        self._users_collection = config.users_collection
        self._ivas_collection = config.ivas_collection
        self._dao_factory = dao_factory

    async def get_user_dao(self) -> UserDao:
        """Construct a DAO for interacting with user data in a database."""
        return await self._dao_factory.get_dao(
            name=self._users_collection,
            dto_model=UserDto,
            id_field="id",
            dto_creation_model=UserCreationDto,
        )

    async def get_iva_dao(self) -> IvaDao:
        """Construct a DAO for interacting with IVA data in a database."""
        return await self._dao_factory.get_dao(
            name=self._ivas_collection,
            dto_model=IvaDto,
            id_field="id",
            dto_creation_model=IvaCreationDto,
        )
