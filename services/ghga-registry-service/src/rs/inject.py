# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Dependency injection and setup of main components"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

import httpx
from fastapi import FastAPI
from ghga_service_commons.auth.ghga import AuthContext, GHGAAuthContextProvider
from hexkit.providers.akafka.provider import (
    ComboTranslator,
    KafkaEventPublisher,
    KafkaEventSubscriber,
)
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import (
    MongoKafkaDaoPublisherFactory,
    PersistentKafkaPublisher,
)

from rs.adapters.inbound.event_sub import OutboxSubTranslator
from rs.adapters.inbound.fastapi_ import dummies
from rs.adapters.inbound.fastapi_.configure import get_configured_app
from rs.adapters.outbound.audit import AuditRepository
from rs.adapters.outbound.dao import get_box_dao, get_file_accession_mapping_dao
from rs.adapters.outbound.event_pub import EventPubTranslator
from rs.adapters.outbound.http import AccessClient, FileBoxClient
from rs.config import Config
from rs.constants import SERVICE_NAME
from rs.core.files import FileController
from rs.core.ghga_registry import GHGARegistry
from rs.core.rdub_manager import RDUBManager
from rs.ports.inbound.ghga_registry import GHGARegistryPort

__all__ = [
    "get_persistent_publisher",
    "prepare_core",
    "prepare_event_subscriber",
    "prepare_rest_app",
]


@asynccontextmanager
async def get_persistent_publisher(
    config: Config, dao_factory: MongoDbDaoFactory | None = None
) -> AsyncGenerator[PersistentKafkaPublisher]:
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
            collection_name="rsPersistedEvents",
        ) as persistent_publisher,
    ):
        yield persistent_publisher


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[GHGARegistryPort]:
    """Constructs and initializes all core components and their outbound dependencies.

    The _override parameters can be used to override the default dependencies.
    """
    async with (
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_publisher_factory,
        MongoDbDaoFactory.construct(config=config) as dao_factory,
        get_persistent_publisher(
            config=config, dao_factory=dao_factory
        ) as persistent_pub_provider,
        httpx.AsyncClient() as httpx_client,
    ):
        event_publisher = EventPubTranslator(
            config=config, provider=persistent_pub_provider
        )
        audit_repository = AuditRepository(
            service=SERVICE_NAME, event_publisher=event_publisher
        )
        file_accession_mapping_dao = await get_file_accession_mapping_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        file_controller = FileController(
            file_accession_mapping_dao=file_accession_mapping_dao
        )
        box_dao = await get_box_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        access_client = AccessClient(config=config, httpx_client=httpx_client)
        file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)

        rdub_manager = RDUBManager(
            box_dao=box_dao,
            file_controller=file_controller,
            audit_repository=audit_repository,
            access_client=access_client,
            file_upload_box_client=file_upload_box_client,
        )

        yield GHGARegistry(rdub_manager=rdub_manager)


def prepare_core_with_override(
    *,
    config: Config,
    ghga_registry_override: GHGARegistryPort | None = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return (
        nullcontext(ghga_registry_override)
        if ghga_registry_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    ghga_registry_override: GHGARegistryPort | None = None,
) -> AsyncGenerator[FastAPI]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the override parameter.
    """
    app = get_configured_app(config=config)

    async with (
        prepare_core_with_override(
            config=config, ghga_registry_override=ghga_registry_override
        ) as ghga_registry,
        GHGAAuthContextProvider.construct(
            config=config,
            context_class=AuthContext,
        ) as auth_context,
    ):
        app.dependency_overrides[dummies.auth_provider] = lambda: auth_context
        app.dependency_overrides[dummies.ghga_registry_port] = lambda: ghga_registry
        yield app


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    ghga_registry_override: GHGARegistryPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the override parameter.
    """
    async with (
        prepare_core_with_override(
            config=config, ghga_registry_override=ghga_registry_override
        ) as ghga_registry,
        KafkaEventPublisher.construct(config=config) as dlq_publisher,
    ):
        outbox_translator = OutboxSubTranslator(
            config=config, ghga_registry=ghga_registry
        )
        translator = ComboTranslator(translators=[outbox_translator])

        async with KafkaEventSubscriber.construct(
            config=config, translator=translator, dlq_publisher=dlq_publisher
        ) as event_subscriber:
            yield event_subscriber
