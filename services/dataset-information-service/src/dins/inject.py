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
#

"""Module hosting the dependency injection container."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from hexkit.providers.akafka import (
    ComboTranslator,
    KafkaEventPublisher,
    KafkaEventSubscriber,
)
from hexkit.providers.mongodb import MongoDbDaoFactory

from dins.adapters.inbound.event_sub import (
    AccessionMapOutboxTranslator,
    EventSubTranslator,
)
from dins.adapters.inbound.fastapi_ import dummies
from dins.adapters.inbound.fastapi_.configure import get_configured_app
from dins.adapters.outbound import dao
from dins.config import Config
from dins.core.information_service import InformationService
from dins.ports.inbound.information_service import InformationServicePort


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[InformationServicePort]:
    """Constructs and initializes all core components and their outbound dependencies."""
    async with MongoDbDaoFactory.construct(config=config) as dao_factory:
        accession_map_dao = await dao.get_file_accession_map_dao(
            dao_factory=dao_factory
        )
        dataset_dao = await dao.get_dataset_dao(dao_factory=dao_factory)
        file_information_dao = await dao.get_file_information_dao(
            dao_factory=dao_factory
        )
        pending_file_info_dao = await dao.get_pending_file_info_dao(
            dao_factory=dao_factory
        )

        yield InformationService(
            accession_map_dao=accession_map_dao,
            dataset_dao=dataset_dao,
            file_information_dao=file_information_dao,
            pending_file_info_dao=pending_file_info_dao,
        )


def prepare_core_with_override(
    *,
    config: Config,
    information_service_override: InformationServicePort | None = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return (
        nullcontext(information_service_override)
        if information_service_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    information_service_override: InformationServicePort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the information_service_override parameter.
    """
    async with prepare_core_with_override(
        config=config, information_service_override=information_service_override
    ) as information_service:
        event_sub_translator = EventSubTranslator(
            config=config, information_service=information_service
        )
        accession_map_subscriber = AccessionMapOutboxTranslator(
            config=config,
            information_service=information_service,
        )
        translator = ComboTranslator(
            translators=[event_sub_translator, accession_map_subscriber]
        )
        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=translator,
                dlq_publisher=dlq_publisher,
            ) as event_subscriber,
        ):
            yield event_subscriber


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    information_service_override: InformationServicePort | None = None,
) -> AsyncGenerator[FastAPI]:
    """Construct and initialize a REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the information_service_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, information_service_override=information_service_override
    ) as information_service:
        app.dependency_overrides[dummies.information_service_port] = lambda: (
            information_service
        )
        yield app
