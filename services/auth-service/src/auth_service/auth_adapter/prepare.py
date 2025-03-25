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

"""Prepare the auth adapter by providing all dependencies"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from ghga_service_commons.api import configure_app
from hexkit.providers.akafka import KafkaEventPublisher
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from auth_service.user_management.claims_repository.deps import get_claim_dao
from auth_service.user_management.claims_repository.translators.dao import (
    ClaimDaoFactory,
)
from auth_service.user_management.user_registry.core.registry import UserRegistry
from auth_service.user_management.user_registry.deps import (
    get_iva_dao,
    get_user_dao,
    get_user_registry,
)
from auth_service.user_management.user_registry.translators.dao import (
    UserDaoPublisherFactory,
)
from auth_service.user_management.user_registry.translators.event_pub import (
    EventPubTranslator,
)

from ..config import Config
from . import DESCRIPTION, TITLE, VERSION
from .adapters.memory_session_store import MemorySessionStore
from .core.totp import TOTPHandler
from .deps import get_session_store, get_totp_handler, get_user_token_dao
from .rest.basic import add_basic_auth_exception_handler
from .rest.router import router
from .translators.dao import UserTokenDaoFactory

__all__ = ["prepare_rest_app"]


@asynccontextmanager
async def prepare_rest_app(config: Config) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize the REST API app along with all its dependencies."""
    app = FastAPI(title=TITLE, description=DESCRIPTION, version=VERSION)
    configure_app(app, config=config)
    add_basic_auth_exception_handler(app, config)
    app.include_router(router)

    session_store = MemorySessionStore(config=config)
    totp_handler = TOTPHandler(config=config)

    dao_factory = MongoDbDaoFactory(config=config)

    async with (
        KafkaEventPublisher.construct(config=config) as event_publisher,
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_publisher_factory,
    ):
        user_token_dao_factory = UserTokenDaoFactory(
            config=config, dao_factory=dao_factory
        )
        user_token_dao = await user_token_dao_factory.get_user_token_dao()

        user_dao_publisher_factory = UserDaoPublisherFactory(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        user_dao = await user_dao_publisher_factory.get_user_dao()
        iva_dao = await user_dao_publisher_factory.get_iva_dao()

        claim_dao_factory = ClaimDaoFactory(config=config, dao_factory=dao_factory)
        claim_dao = await claim_dao_factory.get_claim_dao()

        event_pub = EventPubTranslator(config=config, event_publisher=event_publisher)

        user_registry = UserRegistry(
            config=config,
            user_dao=user_dao,
            iva_dao=iva_dao,
            event_pub=event_pub,
        )

        app.dependency_overrides[get_session_store] = lambda: session_store
        app.dependency_overrides[get_totp_handler] = lambda: totp_handler
        app.dependency_overrides[get_user_registry] = lambda: user_registry

        app.dependency_overrides[get_user_token_dao] = lambda: user_token_dao
        app.dependency_overrides[get_user_dao] = lambda: user_dao
        app.dependency_overrides[get_iva_dao] = lambda: iva_dao
        app.dependency_overrides[get_claim_dao] = lambda: claim_dao

        yield app
