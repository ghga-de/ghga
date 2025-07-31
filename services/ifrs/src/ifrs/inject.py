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
"""Module hosting the dependency injection framework."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from ghga_service_commons.utils.multinode_storage import S3ObjectStorages
from hexkit.providers.akafka import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import PersistentKafkaPublisher

from ifrs.adapters.inbound.event_sub import EventSubTranslator
from ifrs.adapters.outbound import dao
from ifrs.adapters.outbound.event_pub import EventPubTranslator
from ifrs.config import Config
from ifrs.core.file_registry import FileRegistry
from ifrs.ports.inbound.file_registry import FileRegistryPort


@asynccontextmanager
async def get_persistent_publisher(
    config: Config, dao_factory: MongoDbDaoFactory | None = None
) -> AsyncGenerator[PersistentKafkaPublisher, None]:
    """Construct and return a PersistentKafkaPublisher."""
    async with (
        (
            nullcontext(dao_factory)
            if dao_factory
            else MongoDbDaoFactory.construct(config=config)
        ) as _dao_factory,
        PersistentKafkaPublisher.construct(
            config=config,
            dao_factory=_dao_factory,
            compacted_topics={
                config.file_deleted_topic,
                config.file_internally_registered_topic,
            },
            topics_not_stored={config.file_staged_topic},
            collection_name="ifrsPersistedEvents",
        ) as persistent_publisher,
    ):
        yield persistent_publisher


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[FileRegistryPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    object_storages = S3ObjectStorages(config=config)

    async with (
        MongoDbDaoFactory.construct(config=config) as dao_factory,
        get_persistent_publisher(
            config=config, dao_factory=dao_factory
        ) as persistent_kafka_publisher,
    ):
        file_metadata_dao = await dao.get_file_metadata_dao(dao_factory=dao_factory)
        event_publisher = EventPubTranslator(
            config=config, provider=persistent_kafka_publisher
        )
        file_registry = FileRegistry(
            file_metadata_dao=file_metadata_dao,
            event_publisher=event_publisher,
            object_storages=object_storages,
            config=config,
        )
        yield file_registry


def prepare_core_with_override(
    *,
    config: Config,
    core_override: FileRegistryPort | None = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return nullcontext(core_override) if core_override else prepare_core(config=config)


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    core_override: FileRegistryPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as file_registry:
        translator = EventSubTranslator(config=config, file_registry=file_registry)
        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=translator,
                dlq_publisher=dlq_publisher,
            ) as kafka_event_subscriber,
        ):
            yield kafka_event_subscriber
