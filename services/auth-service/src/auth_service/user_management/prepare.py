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

"""Prepare the user management service by providing all dependencies"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from ghga_service_commons.api import configure_app
from hexkit.providers.akafka import KafkaEventPublisher
from hexkit.providers.akafka.provider import KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from auth_service.auth_adapter.deps import get_user_token_dao
from auth_service.auth_adapter.translators.dao import UserTokenDaoFactory

from ..config import Config
from . import CONTACT, DESCRIPTION, LICENSE_INFO, TAGS_METADATA, TITLE, VERSION
from .claims_repository.core.deletion import (
    DatasetDeletionHandler,
    DatasetDeletionPort,
)
from .claims_repository.core.seed import seed_data_steward_claims
from .claims_repository.deps import get_claim_dao
from .claims_repository.rest.router import router as claims_router
from .claims_repository.translators.dao import ClaimDaoFactory
from .claims_repository.translators.event_sub import EventSubTranslator
from .rest.router import router as base_router
from .user_registry.core.registry import UserRegistry
from .user_registry.deps import get_iva_dao, get_user_dao, get_user_registry
from .user_registry.rest.router import router as users_router
from .user_registry.translators.dao import UserDaoPublisherFactory
from .user_registry.translators.event_pub import EventPubTranslator

__all__ = ["prepare_rest_app"]


@asynccontextmanager
async def prepare_event_handler(
    config: Config,
) -> AsyncGenerator[DatasetDeletionPort, None]:
    """Get an event handler for dataset deletion events."""
    dao_factory = MongoDbDaoFactory(config=config)
    claim_dao_factory = ClaimDaoFactory(config=config, dao_factory=dao_factory)
    claim_dao = await claim_dao_factory.get_claim_dao()
    yield DatasetDeletionHandler(claim_dao=claim_dao)


@asynccontextmanager
async def prepare_event_subscriber(
    config: Config,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Get an event subscriber for dataset deletion events."""
    async with prepare_event_handler(config) as handler:
        translator = EventSubTranslator(config=config, handler=handler)
        async with KafkaEventSubscriber.construct(
            config=config, translator=translator
        ) as event_subscriber:
            yield event_subscriber


@asynccontextmanager
async def prepare_rest_app(config: Config) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize the REST API app along with all its dependencies."""
    app = FastAPI(
        title=TITLE,
        description=DESCRIPTION,
        version=VERSION,
        contact=CONTACT,
        license_info=LICENSE_INFO,
        openapi_tags=TAGS_METADATA,
    )
    configure_app(app, config=config)
    app.include_router(base_router)
    apis = config.provide_apis
    with_users_api = "users" in apis
    with_claims_api = "claims" in apis
    if with_users_api:
        app.include_router(users_router)
    if with_claims_api:
        app.include_router(claims_router)

    dao_factory = MongoDbDaoFactory(config=config)

    async with (
        (
            KafkaEventPublisher.construct(config=config)
            if with_users_api
            else nullcontext()
        ) as event_publisher,
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_publisher_factory,
    ):
        user_dao_publisher_factory = UserDaoPublisherFactory(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        user_dao = await user_dao_publisher_factory.get_user_dao()
        app.dependency_overrides[get_user_dao] = lambda: user_dao

        iva_dao = await user_dao_publisher_factory.get_iva_dao()
        app.dependency_overrides[get_iva_dao] = lambda: iva_dao

        claim_dao_factory = ClaimDaoFactory(config=config, dao_factory=dao_factory)
        claim_dao = await claim_dao_factory.get_claim_dao()
        app.dependency_overrides[get_claim_dao] = lambda: claim_dao

        if with_users_api:
            user_token_dao_factory = UserTokenDaoFactory(
                config=config, dao_factory=dao_factory
            )
            user_token_dao = await user_token_dao_factory.get_user_token_dao()
            app.dependency_overrides[get_user_token_dao] = lambda: user_token_dao

            event_pub = EventPubTranslator(
                config=config,
                event_publisher=event_publisher,  # type: ignore
            )
            user_registry = UserRegistry(
                config=config,
                user_dao=user_dao,
                iva_dao=iva_dao,
                event_pub=event_pub,
            )
            app.dependency_overrides[get_user_registry] = lambda: user_registry

        # Seed with data steward claims if started with claims API
        if with_claims_api:
            await seed_data_steward_claims(
                config=config, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
            )

        yield app
