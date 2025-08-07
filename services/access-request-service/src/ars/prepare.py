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
from typing import NamedTuple

from fastapi import FastAPI
from ghga_service_commons.auth.ghga import AuthContext, GHGAAuthContextProvider
from hexkit.providers.akafka import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from ars.adapters.inbound.event_sub import EventSubTranslator
from ars.adapters.inbound.fastapi_ import dummies
from ars.adapters.inbound.fastapi_.configure import get_configured_app
from ars.adapters.outbound.daos import get_access_request_dao, get_dataset_dao
from ars.adapters.outbound.http import AccessGrantsAdapter
from ars.config import Config
from ars.core.repository import AccessRequestRepository
from ars.ports.inbound.repository import AccessRequestRepositoryPort
from ars.ports.outbound.daos import AccessRequestDaoPort


@asynccontextmanager
async def prepare_access_request_dao(
    *,
    config: Config,
) -> AsyncGenerator[AccessRequestDaoPort, None]:
    """Prepare an access request DAO as a context manager"""
    async with MongoKafkaDaoPublisherFactory.construct(
        config=config
    ) as dao_publisher_factory:
        yield await get_access_request_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
) -> AsyncGenerator[AccessRequestRepositoryPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    async with (
        MongoDbDaoFactory.construct(config=config) as dao_factory,
        prepare_access_request_dao(config=config) as access_request_dao,
        AccessGrantsAdapter.construct(config=config) as access_grants,
    ):
        dataset_dao = await get_dataset_dao(dao_factory=dao_factory)
        yield AccessRequestRepository(
            access_request_dao=access_request_dao,
            dataset_dao=dataset_dao,
            access_grants=access_grants,
            config=config,
        )


def _prepare_core_with_override(
    *,
    config: Config,
    repository_override: AccessRequestRepositoryPort | None = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return (
        nullcontext(repository_override)
        if repository_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    repository_override: AccessRequestRepositoryPort | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize a REST API app along with all its dependencies.

    By default, the core dependencies are automatically prepared, but you can also
    provide them using the repository_override parameter.
    """
    app = get_configured_app(config=config)

    async with (
        _prepare_core_with_override(
            config=config, repository_override=repository_override
        ) as access_request_repository,
        GHGAAuthContextProvider.construct(
            config=config, context_class=AuthContext
        ) as auth_context,
    ):
        app.dependency_overrides[dummies.auth_provider] = lambda: auth_context
        app.dependency_overrides[dummies.access_request_repo_port] = (
            lambda: access_request_repository
        )
        yield app


class Consumer(NamedTuple):
    """Container for an event subscriber and the repository that is used."""

    repository: AccessRequestRepositoryPort
    event_subscriber: KafkaEventSubscriber


@asynccontextmanager
async def prepare_consumer(
    *,
    config: Config,
    repository_override: AccessRequestRepositoryPort | None = None,
) -> AsyncGenerator[Consumer, None]:
    """Construct and initialize an event subscriber with all its dependencies.

    By default, the core dependencies are automatically prepared, but you can also
    provide them using the repository_override parameter.
    """
    async with _prepare_core_with_override(
        config=config, repository_override=repository_override
    ) as repository:
        event_sub_translator = EventSubTranslator(repository=repository, config=config)

        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=event_sub_translator,
                dlq_publisher=dlq_publisher,
            ) as event_subscriber,
        ):
            yield Consumer(repository, event_subscriber)
