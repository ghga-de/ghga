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

"""Module hosting the dependency injection container."""

from collections.abc import AsyncGenerator, Coroutine
from contextlib import asynccontextmanager, nullcontext
from typing import Any, TypeAlias

from fastapi import FastAPI
from ghga_service_commons.auth.jwt_auth import JWTAuthContextProvider
from ghga_service_commons.utils.context import asyncnullcontext
from ghga_service_commons.utils.multinode_storage import S3ObjectStorages
from hexkit.providers.akafka import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import PersistentKafkaPublisher

from dcs.adapters.inbound.event_sub import EventSubTranslator
from dcs.adapters.inbound.fastapi_ import dummies
from dcs.adapters.inbound.fastapi_.configure import get_configured_app
from dcs.adapters.outbound.dao import get_drs_dao
from dcs.adapters.outbound.event_pub import EventPubTranslator
from dcs.config import Config
from dcs.core.auth_policies import WorkOrderContext
from dcs.core.data_repository import DataRepository
from dcs.ports.inbound.data_repository import DataRepositoryPort


@asynccontextmanager
async def get_persistent_publisher(
    config: Config, dao_factory: MongoDbDaoFactory | None = None
) -> AsyncGenerator[PersistentKafkaPublisher, None]:
    """Construct and return a PersistentKafkaPublisher."""
    async with (
        (  # use provided factory if supplied or create new one
            nullcontext(dao_factory)
            if dao_factory
            else MongoDbDaoFactory.construct(config=config)
        ) as _dao_factory,
        PersistentKafkaPublisher.construct(
            config=config,
            dao_factory=_dao_factory,
            compacted_topics={
                config.file_deleted_topic,
                config.download_served_topic,
                config.file_registered_for_download_topic,
            },
            topics_not_stored={config.files_to_stage_topic},
            collection_name="dcsPersistedEvents",
        ) as persistent_publisher,
    ):
        yield persistent_publisher


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[DataRepositoryPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    object_storages = S3ObjectStorages(config=config)

    async with (
        MongoDbDaoFactory.construct(config=config) as dao_factory,
        get_persistent_publisher(
            config=config, dao_factory=dao_factory
        ) as persistent_pub_provider,
    ):
        drs_object_dao = await get_drs_dao(dao_factory=dao_factory)
        event_publisher = EventPubTranslator(
            config=config, provider=persistent_pub_provider
        )

        yield DataRepository(
            drs_object_dao=drs_object_dao,
            object_storages=object_storages,
            event_publisher=event_publisher,
            config=config,
        )


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
        app.dependency_overrides[dummies.data_repo_config] = lambda: config
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

        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=event_sub_translator,
                dlq_publisher=dlq_publisher,
            ) as event_subscriber,
        ):
            yield event_subscriber


OutboxCleaner: TypeAlias = Coroutine[Any, Any, None]


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
