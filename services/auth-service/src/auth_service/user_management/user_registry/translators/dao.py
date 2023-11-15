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
from pydantic_settings import BaseSettings

from ..models.dto import User as UserDto
from ..models.dto import UserData as UserCreationDto
from ..ports.dao import UserDao, UserDaoFactoryPort

__all__ = ["UserDaoFactory", "UserDaoFactoryConfig"]


class UserDaoFactoryConfig(BaseSettings):
    """User DAO factory config parameters and their defaults."""

    collection_name: str = "users"


class UserDaoFactory(UserDaoFactoryPort):
    """Translation between UserDaoFactoryPort and DaoFactoryProtocol."""

    def __init__(
        self, *, config: UserDaoFactoryConfig, dao_factory: DaoFactoryProtocol
    ) -> None:
        """Configure with provider for the the DaoFactoryProtocol"""
        self._collection_name = config.collection_name
        self._dao_factory = dao_factory

    async def get_user_dao(self) -> UserDao:
        """Construct a DAO for interacting with user data in a database."""
        return await self._dao_factory.get_dao(
            name=self._collection_name,
            dto_model=UserDto,
            id_field="id",
            dto_creation_model=UserCreationDto,
        )
