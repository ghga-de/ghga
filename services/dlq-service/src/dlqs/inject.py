# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module hosting the dependency injection logic."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from hexkit.protocols.eventpub import EventPublisherProtocol
from hexkit.providers.akafka.provider import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory

from dlqs.adapters.inbound.event_sub import DLQSubTranslator
from dlqs.adapters.inbound.fastapi_ import dummies
from dlqs.adapters.inbound.fastapi_.configure import get_configured_app
from dlqs.adapters.outbound.dao import EventDaoPort, get_aggregator, get_event_dao
from dlqs.config import Config
from dlqs.core.dlq_manager import DLQManager
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from dlqs.ports.outbound.dao import AggregatorPort


@asynccontextmanager
async def get_dao(*, config: Config) -> AsyncGenerator[EventDaoPort]:
    """Constructs and initializes the DAO factory."""
    async with MongoDbDaoFactory.construct(config=config) as dao_factory:
        dao = await get_event_dao(dao_factory=dao_factory)
        yield dao


@asynccontextmanager
async def get_event_publisher(
    *, config: Config
) -> AsyncGenerator[EventPublisherProtocol]:
    """Constructs and initializes the retry-topic event publisher."""
    async with KafkaEventPublisher.construct(config=config) as publisher:
        yield publisher


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
    dao_override: EventDaoPort | None = None,
    aggregator_override: AggregatorPort | None = None,
    publisher_override: EventPublisherProtocol | None = None,
) -> AsyncGenerator[DLQManagerPort]:
    """Constructs and initializes all core components and their outbound dependencies.

    The _override parameters can be used to override the default dependencies.
    """
    async with (
        nullcontext(publisher_override)
        if publisher_override
        else get_event_publisher(config=config) as publisher,
        nullcontext(dao_override) if dao_override else get_dao(config=config) as dao,
        nullcontext(aggregator_override)
        if aggregator_override
        else get_aggregator(config=config) as aggregator,
    ):
        yield DLQManager(
            config=config, publisher=publisher, dao=dao, aggregator=aggregator
        )


def prepare_core_with_override(
    *, config: Config, dlq_manager_override: DLQManagerPort | None = None
):
    """Resolve the dlq_manager context manager based on config and override (if any)."""
    return (
        nullcontext(dlq_manager_override)
        if dlq_manager_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    dlq_manager_override: DLQManagerPort | None = None,
) -> AsyncGenerator[FastAPI]:
    """Construct and initialize a REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the dlq_manager_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config,
        dlq_manager_override=dlq_manager_override,
    ) as dlq_manager:
        app.dependency_overrides[dummies.config_dummy] = lambda: config
        app.dependency_overrides[dummies.dlq_manager_port] = lambda: dlq_manager
        yield app


@asynccontextmanager
async def prepare_dlq_subscriber(
    *,
    config: Config,
    dlq_manager_override: DLQManagerPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the override parameter.
    """
    async with prepare_core_with_override(
        config=config, dlq_manager_override=dlq_manager_override
    ) as dlq_manager:
        dlq_sub_translator = DLQSubTranslator(dlq_manager=dlq_manager)
        async with KafkaEventSubscriber.construct(
            config=config, translator=dlq_sub_translator
        ) as dlq_subscriber:
            yield dlq_subscriber
