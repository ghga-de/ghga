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

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from ghga_service_commons.utils.context import asyncnullcontext
from ghga_service_commons.utils.multinode_storage import S3ObjectStorages
from hexkit.providers.akafka import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import PersistentKafkaPublisher

from ucs.adapters.inbound.event_sub import EventSubTranslator
from ucs.adapters.inbound.fastapi_ import dummies
from ucs.adapters.inbound.fastapi_.configure import get_configured_app
from ucs.adapters.outbound.dao import DaoCollectionTranslator
from ucs.adapters.outbound.event_pub import EventPubTranslator
from ucs.config import Config
from ucs.core.file_service import FileMetadataServive
from ucs.core.storage_inspector import InboxInspector
from ucs.core.upload_service import UploadService
from ucs.ports.inbound.file_service import FileMetadataServicePort
from ucs.ports.inbound.upload_service import UploadServicePort


@asynccontextmanager
async def get_persistent_publisher(
    config: Config, dao_factory: MongoDbDaoFactory | None = None
) -> AsyncGenerator[PersistentKafkaPublisher, None]:
    """Construct and return a PersistentKafkaPublisher."""
    dao_factory = dao_factory or MongoDbDaoFactory(config=config)
    async with PersistentKafkaPublisher.construct(
        config=config,
        dao_factory=dao_factory,
        compacted_topics={config.file_deleted_topic, config.file_upload_received_topic},
        collection_name="ucsPersistedEvents",
    ) as persistent_publisher:
        yield persistent_publisher


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
) -> AsyncGenerator[tuple[UploadServicePort, FileMetadataServicePort], None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    object_storages = S3ObjectStorages(config=config)
    dao_factory = MongoDbDaoFactory(config=config)
    dao_collection = await DaoCollectionTranslator.construct(provider=dao_factory)

    async with get_persistent_publisher(config=config) as persistent_publisher:
        event_pub_translator = EventPubTranslator(
            config=config, provider=persistent_publisher
        )
        upload_service = UploadService(
            daos=dao_collection,
            object_storages=object_storages,
            event_publisher=event_pub_translator,
        )
        file_metadata_service = FileMetadataServive(daos=dao_collection)
        yield upload_service, file_metadata_service


def prepare_core_with_override(
    *,
    config: Config,
    core_override: tuple[UploadServicePort, FileMetadataServicePort] | None = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return (
        asyncnullcontext(core_override)
        if core_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    core_override: tuple[UploadServicePort, FileMetadataServicePort] | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize a REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as (
        upload_service,
        file_metadata_service,
    ):
        app.dependency_overrides[dummies.file_metadata_service_port] = (
            lambda: file_metadata_service
        )
        app.dependency_overrides[dummies.upload_service_port] = lambda: upload_service
        yield app


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    core_override: tuple[UploadServicePort, FileMetadataServicePort] | None = None,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as (upload_service, file_metadata_service):
        event_sub_translator = EventSubTranslator(
            file_metadata_service=file_metadata_service,
            upload_service=upload_service,
            config=config,
        )

        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=event_sub_translator,
                dlq_publisher=dlq_publisher,
            ) as kafka_event_subscriber,
        ):
            yield kafka_event_subscriber


@asynccontextmanager
async def prepare_storage_inspector(*, config: Config):
    """Alternative to prepare_core for storage inspection CLI command without Kafka."""
    object_storages = S3ObjectStorages(config=config)
    dao_factory = MongoDbDaoFactory(config=config)
    dao_collection = await DaoCollectionTranslator.construct(provider=dao_factory)

    yield InboxInspector(
        config=config, daos=dao_collection, object_storages=object_storages
    )
