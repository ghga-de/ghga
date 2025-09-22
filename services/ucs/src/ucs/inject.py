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

"""Module hosting the dependency injection container."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from ghga_service_commons.utils.multinode_storage import S3ObjectStorages
from hexkit.providers.akafka import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongokafka.provider import MongoKafkaDaoPublisherFactory

from ucs.adapters.inbound.event_sub import EventSubTranslator
from ucs.adapters.inbound.fastapi_ import dummies
from ucs.adapters.inbound.fastapi_.configure import get_configured_app
from ucs.adapters.inbound.fastapi_.http_authorization import (
    JWTAuthContextProviderBundle,
)
from ucs.adapters.outbound.dao import (
    UploadDaoPublisherFactory,
    get_s3_upload_details_dao,
)
from ucs.config import Config
from ucs.core.controller import UploadController
from ucs.ports.inbound.controller import UploadControllerPort


@asynccontextmanager
async def prepare_outbox_publisher(
    *, config: Config
) -> AsyncGenerator[UploadDaoPublisherFactory]:
    """Prepare an outbox publisher (to be used by main module)"""
    async with MongoKafkaDaoPublisherFactory.construct(
        config=config
    ) as dao_pub_factory:
        yield UploadDaoPublisherFactory(
            config=config, dao_publisher_factory=dao_pub_factory
        )


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
) -> AsyncGenerator[UploadControllerPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    object_storages = S3ObjectStorages(config=config)

    async with (
        MongoDbDaoFactory.construct(config=config) as dao_factory,
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_pub_factory,
    ):
        upload_dao_factory = UploadDaoPublisherFactory(
            config=config, dao_publisher_factory=dao_pub_factory
        )
        file_upload_box_dao = await upload_dao_factory.get_file_upload_box_dao()
        file_upload_dao = await upload_dao_factory.get_file_upload_dao()
        s3_upload_details_dao = await get_s3_upload_details_dao(dao_factory=dao_factory)

        controller = UploadController(
            config=config,
            file_upload_box_dao=file_upload_box_dao,
            file_upload_dao=file_upload_dao,
            s3_upload_details_dao=s3_upload_details_dao,
            object_storages=object_storages,
        )
        yield controller


def prepare_core_with_override(
    *,
    config: Config,
    core_override: UploadControllerPort | None = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return nullcontext(core_override) if core_override else prepare_core(config=config)


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    core_override: UploadControllerPort | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize a REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    app = get_configured_app(config=config)

    async with (
        prepare_core_with_override(
            config=config, core_override=core_override
        ) as upload_controller,
    ):
        auth_provider_bundle = JWTAuthContextProviderBundle(config=config)
        app.dependency_overrides[dummies.auth_provider_bundle] = (
            lambda: auth_provider_bundle
        )
        app.dependency_overrides[dummies.upload_controller_port] = (
            lambda: upload_controller
        )
        yield app


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    core_override: UploadControllerPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as controller:
        event_sub_translator = EventSubTranslator(
            config=config,
            upload_controller=controller,
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
