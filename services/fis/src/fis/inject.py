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
from ghga_service_commons.auth.jwt_auth import JWTAuthConfig, JWTAuthContextProvider
from hexkit.providers.akafka import (
    ComboTranslator,
    KafkaEventPublisher,
    KafkaEventSubscriber,
)
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka import PersistentKafkaPublisher

from fis.adapters.inbound.event_sub import OutboxSubTranslator
from fis.adapters.inbound.fastapi_ import dummies
from fis.adapters.inbound.fastapi_.configure import get_configured_app
from fis.adapters.inbound.fastapi_.http_authorization import JWT
from fis.adapters.outbound.dao import get_file_dao, get_interrogation_report_dao
from fis.adapters.outbound.event_pub import EventPubTranslator
from fis.adapters.outbound.http import get_configured_httpx_client
from fis.adapters.outbound.secrets import SecretsClient
from fis.config import Config
from fis.constants import AUTH_CHECK_CLAIMS
from fis.core.interrogation import InterrogationHandler, InterrogationHandlerPort


@asynccontextmanager
async def get_persistent_publisher(
    config: Config, dao_factory: MongoDbDaoFactory | None = None
) -> AsyncGenerator[PersistentKafkaPublisher]:
    """Construct and return a PersistentKafkaPublisher."""
    async with (
        (
            nullcontext(dao_factory)
            if dao_factory
            else MongoDbDaoFactory.construct(config=config)
        ) as _dao_factory,
        PersistentKafkaPublisher.construct(
            config=config,
            dao_factory=_dao_factory,
            compacted_topics={config.file_interrogations_topic},
            collection_name="fisPersistedEvents",
        ) as persistent_publisher,
    ):
        yield persistent_publisher


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[InterrogationHandlerPort]:
    """Constructs and initializes all core components and their outbound dependencies."""
    async with (
        MongoDbDaoFactory.construct(config=config) as dao_factory,
        get_persistent_publisher(
            config=config, dao_factory=dao_factory
        ) as persistent_publisher,
        get_configured_httpx_client(config=config) as httpx_client,
    ):
        file_dao = await get_file_dao(dao_factory=dao_factory)
        interrogation_report_dao = await get_interrogation_report_dao(
            dao_factory=dao_factory
        )
        event_publisher = EventPubTranslator(
            config=config, provider=persistent_publisher
        )
        secrets_client = SecretsClient(config=config, httpx_client=httpx_client)
        yield InterrogationHandler(
            config=config,
            file_dao=file_dao,
            interrogation_report_dao=interrogation_report_dao,
            event_publisher=event_publisher,
            secrets_client=secrets_client,
        )


def prepare_core_with_override(
    *,
    config: Config,
    core_override: InterrogationHandlerPort | None = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return nullcontext(core_override) if core_override else prepare_core(config=config)


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    core_override: InterrogationHandlerPort | None = None,
) -> AsyncGenerator[FastAPI]:
    """Construct and initialize a REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as interrogator:
        app.dependency_overrides[dummies.interrogator_dummy] = lambda: interrogator

        # Configure JWT auth provider for each known data hub
        auth_providers = {}
        for hub, auth_key in config.data_hub_auth_keys.items():
            auth_config = JWTAuthConfig(
                auth_key=auth_key,
                auth_check_claims=dict.fromkeys(AUTH_CHECK_CLAIMS),
            )
            provider = JWTAuthContextProvider(config=auth_config, context_class=JWT)
            auth_providers[hub] = provider

        app.dependency_overrides[dummies.auth_providers_dummy] = lambda: auth_providers

        yield app


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    core_override: InterrogationHandlerPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the override parameter.
    """
    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as interrogation_handler:
        file_upload_translator = OutboxSubTranslator(
            config=config,
            interrogation_handler=interrogation_handler,
        )
        combo_translator = ComboTranslator(translators=[file_upload_translator])

        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=combo_translator,
                dlq_publisher=dlq_publisher,
            ) as event_subscriber,
        ):
            yield event_subscriber
