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

"""DAOs that are used as part of the outbound port for the auth adapter."""

from abc import ABC, abstractmethod
from typing import TypeAlias

from hexkit.protocols.dao import Dao
from pydantic import BaseModel, ConfigDict, Field

from ..core.totp import TOTPToken

__all__ = ["UserToken", "UserTokenDaoFactoryPort"]


class UserToken(BaseModel):
    """Model for a TOTP token bound to a user

    For security reasons, we store the TOTP tokens in a separate collection.
    """

    user_id: str = Field(
        default=..., description="The user ID of the user who owns the TOTP token"
    )
    totp_token: TOTPToken = Field(default=..., description="The TOTP token of the user")

    model_config = ConfigDict(extra="forbid", frozen=True)


UserTokenDao: TypeAlias = Dao[UserToken]


class UserTokenDaoFactoryPort(ABC):
    """Port that provides a factory for user TOTP token data access objects."""

    @abstractmethod
    async def get_user_token_dao(self) -> UserTokenDao:
        """Construct a DAO for interacting with user data in a database."""
        ...
