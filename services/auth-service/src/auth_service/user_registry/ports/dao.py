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

"""DAOs that are used as part of the outbound port for the user registry."""

from abc import ABC, abstractmethod
from typing import TypeAlias  # in typing only since Python 3.10

from hexkit.protocols.daopub import DaoPublisher

from ..models.ivas import Iva as IvaDto
from ..models.users import User as UserDto

__all__ = ["IvaDao", "UserDao", "UserDaoPublisherFactoryPort"]


UserDao: TypeAlias = DaoPublisher[UserDto]
IvaDao: TypeAlias = DaoPublisher[IvaDto]


class UserDaoPublisherFactoryPort(ABC):
    """Port that provides a factory for user related data access objects.

    These objects will also publish changes according to the outbox pattern.
    """

    @abstractmethod
    async def get_user_dao(self) -> UserDao:
        """Construct a DAO for interacting with user data in a database."""
        ...

    @abstractmethod
    async def get_iva_dao(self) -> IvaDao:
        """Construct a DAO for interacting with IVA data in a database."""
        ...
