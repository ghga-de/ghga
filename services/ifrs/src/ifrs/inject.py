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
"""Module hosting the dependency injection framework."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from ghga_service_commons.utils.context import asyncnullcontext
from ghga_service_commons.utils.multinode_storage import S3ObjectStorages
from hexkit.providers.akafka import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory

from ifrs.adapters.inbound.event_sub import EventSubTranslator
from ifrs.adapters.outbound.dao import FileMetadataDaoConstructor
from ifrs.adapters.outbound.event_pub import EventPubTranslator
from ifrs.config import Config
from ifrs.core.file_registry import FileRegistry
from ifrs.ports.inbound.file_registry import FileRegistryPort


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[FileRegistryPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    dao_factory = MongoDbDaoFactory(config=config)
    object_storages = S3ObjectStorages(config=config)
    file_metadata_dao = await FileMetadataDaoConstructor.construct(
        dao_factory=dao_factory
    )

    async with KafkaEventPublisher.construct(config=config) as kafka_event_publisher:
        event_publisher = EventPubTranslator(
            config=config, provider=kafka_event_publisher
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
    core_override: Optional[FileRegistryPort] = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return (
        asyncnullcontext(core_override)
        if core_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_event_subscriber(
    *, config: Config, core_override: Optional[FileRegistryPort] = None
):
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as file_registry:
        event_sub_translator = EventSubTranslator(
            file_registry=file_registry, config=config
        )
        async with KafkaEventSubscriber.construct(
            config=config, translator=event_sub_translator
        ) as kafka_event_subscriber:
            yield kafka_event_subscriber
