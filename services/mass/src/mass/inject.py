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
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from hexkit.providers.akafka.provider import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb.provider import MongoDbDaoFactory

from mass.adapters.inbound.event_sub import EventSubTranslator
from mass.adapters.inbound.fastapi_ import dummies
from mass.adapters.inbound.fastapi_.configure import get_configured_app
from mass.adapters.outbound.aggregator import AggregatorCollection, AggregatorFactory
from mass.adapters.outbound.dao import DaoCollection
from mass.config import Config
from mass.core.query_handler import QueryHandler
from mass.ports.inbound.query_handler import QueryHandlerPort


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[QueryHandlerPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    async with (
        AggregatorFactory.construct(config=config) as aggregator_factory,
        MongoDbDaoFactory.construct(config=config) as dao_factory,
    ):
        dao_collection = await DaoCollection.construct(
            dao_factory=dao_factory, config=config
        )
        aggregator_collection = await AggregatorCollection.construct(
            aggregator_factory=aggregator_factory, config=config
        )

        yield QueryHandler(
            config=config,
            aggregator_collection=aggregator_collection,
            dao_collection=dao_collection,
        )


def prepare_core_with_override(
    *, config: Config, query_handler_override: QueryHandlerPort | None = None
):
    """Resolve the query_handler context manager based on config and override (if any)."""
    return (
        nullcontext(query_handler_override)
        if query_handler_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    query_handler_override: QueryHandlerPort | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the query_handler_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, query_handler_override=query_handler_override
    ) as query_handler:
        app.dependency_overrides[dummies.config_dummy] = lambda: config
        app.dependency_overrides[dummies.query_handler_port] = lambda: query_handler
        yield app


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    query_handler_override: QueryHandlerPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the query_handler_override parameter.
    """
    async with prepare_core_with_override(
        config=config, query_handler_override=query_handler_override
    ) as query_handler:
        event_sub_translator = EventSubTranslator(
            query_handler=query_handler,
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
