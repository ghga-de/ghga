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

from pcs.adapters.inbound.fastapi_ import dummies
from pcs.adapters.inbound.fastapi_.configure import get_configured_app
from pcs.adapters.outbound.event_pub import EventPubTranslator
from pcs.config import Config
from pcs.core.file_deletion import FileDeletion
from pcs.ports.inbound.file_deletion import FileDeletionPort


@asynccontextmanager
async def get_persistent_publisher(
    config: Config, dao_factory: MongoDbDaoFactory | None = None
) -> AsyncGenerator[PersistentKafkaPublisher, None]:
    """Construct and return a PersistentKafkaPublisher."""
    dao_factory = dao_factory or MongoDbDaoFactory(config=config)
    async with PersistentKafkaPublisher.construct(
        config=config,
        dao_factory=dao_factory,
        compacted_topics={config.file_deletion_request_topic},
        collection_name="pcsPersistedEvents",
    ) as persistent_publisher:
        yield persistent_publisher


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[FileDeletionPort, None]:
    """Construct and initialize the core component and its outbound dependencies."""
    resource = Resource(attributes={SERVICE_NAME: "Purge Controller Service"})
    trace_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    trace_provider.add_span_processor(processor)
    trace.set_tracer_provider(trace_provider)

    dao_factory = MongoDbDaoFactory(config=config)
    async with get_persistent_publisher(
        config=config, dao_factory=dao_factory
    ) as persistent_publisher:
        event_pub_translator = EventPubTranslator(
            config=config, provider=persistent_publisher
        )
        file_deletion = FileDeletion(event_publisher=event_pub_translator)
        yield file_deletion


def prepare_core_with_override(
    *,
    config: Config,
    core_override: FileDeletionPort | None = None,
):
    """Return a context manager for preparing the core that can be overwritten
    with the given value.
    """
    return (
        asyncnullcontext(core_override)
        if core_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    core_override: FileDeletionPort | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as file_deletion:
        app.dependency_overrides[dummies.token_hash_config] = lambda: config
        app.dependency_overrides[dummies.file_deletion] = lambda: file_deletion
        yield app
