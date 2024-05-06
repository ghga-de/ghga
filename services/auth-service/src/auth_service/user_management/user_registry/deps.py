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

"""FastAPI dependencies for the user registry"""

from collections.abc import AsyncGenerator
from typing import Annotated

from hexkit.protocols.eventpub import EventPublisherProtocol
from hexkit.providers.akafka import KafkaConfig, KafkaEventPublisher

from auth_service.deps import (
    Depends,
    MongoDbDaoFactory,
    get_config,
    get_mongodb_dao_factory,
)

from .core.registry import UserRegistry, UserRegistryConfig
from .ports.dao import IvaDao, UserDao
from .ports.event_pub import EventPublisherPort
from .ports.registry import UserRegistryPort
from .translators.dao import UserDaoConfig, UserDaoFactory
from .translators.event_pub import EventPubTranslator, EventPubTranslatorConfig

__all__ = ["get_user_dao", "IvaDao", "UserDao", "get_user_registry"]


def get_user_dao_factory(
    config: Annotated[UserDaoConfig, Depends(get_config)],
    dao_factory: Annotated[MongoDbDaoFactory, Depends(get_mongodb_dao_factory)],
) -> UserDaoFactory:
    """Get user DAO factory."""
    return UserDaoFactory(config=config, dao_factory=dao_factory)


async def get_user_dao(
    dao_factory: Annotated[UserDaoFactory, Depends(get_user_dao_factory)],
) -> UserDao:
    """Get user data access object."""
    return await dao_factory.get_user_dao()


async def get_iva_dao(
    dao_factory: Annotated[UserDaoFactory, Depends(get_user_dao_factory)],
) -> IvaDao:
    """Get IVA data access object."""
    return await dao_factory.get_iva_dao()


async def get_event_publisher(
    config: Annotated[KafkaConfig, Depends(get_config)],
) -> AsyncGenerator[EventPublisherProtocol, None]:
    async with KafkaEventPublisher.construct(config=config) as publisher:
        yield publisher


async def get_event_pub_translator(
    config: Annotated[EventPubTranslatorConfig, Depends(get_config)],
    event_publisher: Annotated[EventPublisherProtocol, Depends(get_event_publisher)],
) -> EventPublisherPort:
    """Get event publisher."""
    return EventPubTranslator(config=config, event_publisher=event_publisher)


async def get_user_registry(
    config: Annotated[UserRegistryConfig, Depends(get_config)],
    user_dao: Annotated[UserDao, Depends(get_user_dao)],
    iva_dao: Annotated[IvaDao, Depends(get_iva_dao)],
    event_pub: Annotated[EventPublisherPort, Depends(get_event_pub_translator)],
) -> UserRegistryPort:
    """Get user registry."""
    return UserRegistry(
        config=config, user_dao=user_dao, iva_dao=iva_dao, event_pub=event_pub
    )
