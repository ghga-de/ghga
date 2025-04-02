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

"""Module hosting the dependency injection container."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from ghga_service_commons.utils.context import asyncnullcontext
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import PersistentKafkaPublisher
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from fis.adapters.inbound.fastapi_ import dummies
from fis.adapters.inbound.fastapi_.configure import get_configured_app
from fis.adapters.outbound.dao import get_file_dao
from fis.adapters.outbound.event_pub import EventPubTranslator
from fis.adapters.outbound.vault import VaultAdapter
from fis.config import Config
from fis.core.ingest import LegacyUploadMetadataProcessor, UploadMetadataProcessor
from fis.ports.inbound.ingest import (
    LegacyUploadMetadataProcessorPort,
    UploadMetadataProcessorPort,
)


@asynccontextmanager
async def get_persistent_publisher(
    config: Config, dao_factory: MongoDbDaoFactory | None = None
) -> AsyncGenerator[PersistentKafkaPublisher, None]:
    """Construct and return a PersistentKafkaPublisher."""
    dao_factory = dao_factory or MongoDbDaoFactory(config=config)
    async with PersistentKafkaPublisher.construct(
        config=config,
        dao_factory=dao_factory,
        compacted_topics={config.file_interrogations_topic},
        collection_name="fisPersistedEvents",
    ) as persistent_publisher:
        yield persistent_publisher


@asynccontextmanager
async def prepare_core(
    *, config: Config
) -> AsyncGenerator[
    tuple[UploadMetadataProcessorPort, LegacyUploadMetadataProcessorPort], None
]:
    """Constructs and initializes all core components and their outbound dependencies."""
    resource = Resource(attributes={SERVICE_NAME: "File Ingest Service"})
    trace_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    trace_provider.add_span_processor(processor)
    trace.set_tracer_provider(trace_provider)

    vault_adapter = VaultAdapter(config=config)
    dao_factory = MongoDbDaoFactory(config=config)
    file_dao = await get_file_dao(dao_factory=dao_factory)

    async with get_persistent_publisher(
        config=config, dao_factory=dao_factory
    ) as persistent_publisher:
        event_publisher = EventPubTranslator(
            config=config, provider=persistent_publisher
        )
        yield (
            UploadMetadataProcessor(
                config=config,
                event_publisher=event_publisher,
                vault_adapter=vault_adapter,
                file_dao=file_dao,
            ),
            LegacyUploadMetadataProcessor(
                config=config,
                event_publisher=event_publisher,
                vault_adapter=vault_adapter,
                file_dao=file_dao,
            ),
        )


def prepare_core_with_override(
    *,
    config: Config,
    core_override: tuple[UploadMetadataProcessorPort, LegacyUploadMetadataProcessorPort]
    | None = None,
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
    core_override: tuple[UploadMetadataProcessorPort, LegacyUploadMetadataProcessorPort]
    | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize a REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as (
        upload_metadata_processor,
        legacy_upload_metadata_processor,
    ):
        app.dependency_overrides[dummies.config_dummy] = lambda: config

        app.dependency_overrides[dummies.upload_processor_port] = (
            lambda: upload_metadata_processor
        )

        app.dependency_overrides[dummies.legacy_upload_processor] = (
            lambda: legacy_upload_metadata_processor
        )

        yield app
