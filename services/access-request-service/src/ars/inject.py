# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from fastapi import FastAPI
from ghga_service_commons.auth.ghga import AuthContext, GHGAAuthContextProvider
from ghga_service_commons.utils.context import asyncnullcontext
from hexkit.providers.akafka import KafkaEventPublisher
from hexkit.providers.mongodb import MongoDbDaoFactory

from ars.adapters.inbound.fastapi_ import dummies
from ars.adapters.inbound.fastapi_.configure import get_configured_app
from ars.adapters.outbound.dao import AccessRequestDaoConstructor
from ars.adapters.outbound.event_pub import EventPubTranslator
from ars.adapters.outbound.http import AccessGrantsAdapter
from ars.config import Config
from ars.core.repository import AccessRequestRepository
from ars.ports.inbound.repository import AccessRequestRepositoryPort


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
) -> AsyncGenerator[AccessRequestRepositoryPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    dao_factory = MongoDbDaoFactory(config=config)
    access_request_dao = await AccessRequestDaoConstructor.construct(
        dao_factory=dao_factory
    )
    async with (
        KafkaEventPublisher.construct(config=config) as event_publisher,
        AccessGrantsAdapter.construct(config=config) as access_grants,
    ):
        event_publisher = EventPubTranslator(
            config=config, event_publisher=event_publisher
        )
        yield AccessRequestRepository(
            access_request_dao=access_request_dao,
            event_publisher=event_publisher,
            access_grants=access_grants,
            config=config,
        )


def prepare_core_with_override(
    *,
    config: Config,
    core_override: Optional[AccessRequestRepositoryPort] = None,
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
    core_override: Optional[AccessRequestRepositoryPort] = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize a REST API app along with all its dependencies.

    By default, the core dependencies are automatically prepared, but you can also
    provide them using the core_override parameter.
    """
    app = get_configured_app(config=config)

    async with (
        prepare_core_with_override(
            config=config, core_override=core_override
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
