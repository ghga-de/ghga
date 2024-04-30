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

"""Translation between general and user token specific DAOs."""

from hexkit.protocols.dao import DaoFactoryProtocol

from auth_service.user_management.user_registry.translators.dao import UserDaoConfig

from ..ports.dao import UserToken, UserTokenDao, UserTokenDaoFactoryPort

__all__ = ["UserTokenDaoFactory"]


class UserTokenDaoFactory(UserTokenDaoFactoryPort):
    """Translation between UserTokenDaoFactoryPort and DaoFactoryProtocol."""

    def __init__(
        self, *, config: UserDaoConfig, dao_factory: DaoFactoryProtocol
    ) -> None:
        """Configure with provider for the DaoFactoryProtocol"""
        self._collection = config.user_tokens_collection
        self._dao_factory = dao_factory

    async def get_user_token_dao(self) -> UserTokenDao:
        """Construct a DAO for interacting with user TOTP tokens in a database."""
        return await self._dao_factory.get_dao(
            name=self._collection,
            dto_model=UserToken,
            id_field="user_id",
        )
