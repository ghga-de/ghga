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

"""Translation between general and user specific DAOs."""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs import IvaChangeEventsConfig, UserEventsConfig
from hexkit.custom_types import JsonObject
from hexkit.protocols.daopub import DaoPublisher, DaoPublisherFactoryProtocol
from pydantic import Field

from ..models.ivas import Iva as IvaDto
from ..models.users import User as UserDto
from ..ports.dao import UserDaoPublisherFactoryPort

__all__ = ["UserDaoConfig", "UserDaoPublisherFactory"]


class UserDaoConfig(UserEventsConfig, IvaChangeEventsConfig):
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


class UserDaoPublisherFactory(UserDaoPublisherFactoryPort):
    """Translation between UserDaoPublisherFactoryPort and DaoPublisherFactoryProtocol."""

    def __init__(
        self,
        *,
        config: UserDaoConfig,
        dao_publisher_factory: DaoPublisherFactoryProtocol,
    ) -> None:
        """Configure with provider for the DaoFactoryProtocol"""
        self._users_collection = config.users_collection
        self._ivas_collection = config.ivas_collection
        self._user_topic = config.user_topic
        self._iva_state_changed_topic = config.iva_state_changed_topic
        self._dao_publisher_factory = dao_publisher_factory

    @staticmethod
    def _user_to_event(user: UserDto) -> JsonObject:
        """Translate a user to an event."""
        validated_user = event_schemas.User(
            user_id=user.id,
            name=user.name,
            email=user.email,
            title=user.title.value if user.title else None,  # pyright: ignore
        )
        return validated_user.model_dump()

    async def get_user_dao(self) -> DaoPublisher[UserDto]:
        """Construct a DAO for interacting with user data in a database.

        This DAO automatically publishes changes as events.
        """
        return await self._dao_publisher_factory.get_dao(
            name=self._users_collection,
            dto_model=UserDto,
            id_field="id",
            dto_to_event=self._user_to_event,
            event_topic=self._user_topic,
            autopublish=True,
        )

    async def get_iva_dao(self) -> DaoPublisher[IvaDto]:
        """Construct a DAO for interacting with IVA data in a database.

        This DAO does not automatically publish changes as events,
        since we are currently using specific events for state changes.
        """
        return await self._dao_publisher_factory.get_dao(
            name=self._ivas_collection,
            dto_model=IvaDto,
            id_field="id",
            dto_to_event=lambda dto: None,
            event_topic=self._iva_state_changed_topic,
            autopublish=False,
        )
