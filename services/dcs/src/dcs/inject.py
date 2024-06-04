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

"""Module hosting the dependency injection container."""

from collections.abc import AsyncGenerator, Coroutine
from contextlib import asynccontextmanager
from typing import Any, TypeAlias

from fastapi import FastAPI
from ghga_service_commons.auth.jwt_auth import JWTAuthContextProvider
from ghga_service_commons.utils.context import asyncnullcontext
from ghga_service_commons.utils.multinode_storage import S3ObjectStorages
from hexkit.providers.akafka import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory

from dcs.adapters.inbound.event_sub import EventSubTranslator
from dcs.adapters.inbound.fastapi_ import dummies
from dcs.adapters.inbound.fastapi_.configure import get_configured_app
from dcs.adapters.outbound.dao import DrsObjectDaoConstructor
from dcs.adapters.outbound.event_pub import EventPubTranslator
from dcs.config import Config
from dcs.core.auth_policies import WorkOrderContext
from dcs.core.data_repository import DataRepository
from dcs.ports.inbound.data_repository import DataRepositoryPort


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[DataRepositoryPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    dao_factory = MongoDbDaoFactory(config=config)
    drs_object_dao = await DrsObjectDaoConstructor.construct(dao_factory=dao_factory)
    object_storages = S3ObjectStorages(config=config)

    async with KafkaEventPublisher.construct(config=config) as event_pub_provider:
        event_publisher = EventPubTranslator(config=config, provider=event_pub_provider)

        yield DataRepository(
            drs_object_dao=drs_object_dao,
            object_storages=object_storages,
            event_publisher=event_publisher,
            config=config,
        )


OutboxCleaner: TypeAlias = Coroutine[Any, Any, None]


def prepare_core_with_override(
    *,
    config: Config,
    data_repo_override: DataRepositoryPort | None = None,
):
    """Resolve the data_repo context manager based on config and override (if any)."""
    return (
        asyncnullcontext(data_repo_override)
        if data_repo_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    data_repo_override: DataRepositoryPort | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the data_repo_override parameter.
    """
    app = get_configured_app(config=config)

    async with (
        prepare_core_with_override(
            config=config, data_repo_override=data_repo_override
        ) as data_repository,
        JWTAuthContextProvider.construct(
            config=config, context_class=WorkOrderContext
        ) as auth_context,
    ):
        app.dependency_overrides[dummies.auth_provider] = lambda: auth_context
        app.dependency_overrides[dummies.data_repo_port] = lambda: data_repository
        yield app


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    data_repo_override: DataRepositoryPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the data_repo_override parameter.
    """
    async with prepare_core_with_override(
        config=config, data_repo_override=data_repo_override
    ) as data_repository:
        event_sub_translator = EventSubTranslator(
            data_repository=data_repository,
            config=config,
        )

        async with KafkaEventSubscriber.construct(
            config=config, translator=event_sub_translator
        ) as event_subscriber:
            yield event_subscriber


@asynccontextmanager
async def prepare_outbox_cleaner(
    *,
    config: Config,
    data_repo_override: DataRepositoryPort | None = None,
) -> AsyncGenerator[OutboxCleaner, None]:
    """Construct and initialize a coroutine that cleans the outbox once invoked.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the data_repo_override parameter.
    """
    async with prepare_core_with_override(
        config=config, data_repo_override=data_repo_override
    ) as data_repository:
        yield data_repository.cleanup_outbox_buckets(object_storages_config=config)
