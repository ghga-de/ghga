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

"""Module hosting the code to prepare the application by providing dependencies."""

from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from typing import NamedTuple

from fastapi import FastAPI
from ghga_service_commons.auth.ghga import AuthContext, GHGAAuthContextProvider
from hexkit.providers.akafka import (
    ComboTranslator,
    KafkaEventPublisher,
    KafkaEventSubscriber,
)
from hexkit.providers.mongodb import MongoDbDaoFactory

from wps.adapters.inbound.event_sub import (
    AccessionMapOutboxTranslator,
    EventSubTranslator,
    RDUBOutboxTranslator,
)
from wps.adapters.inbound.fastapi_ import dummies
from wps.adapters.inbound.fastapi_.configure import get_configured_app
from wps.adapters.outbound.dao import (
    get_accession_map_dao,
    get_dataset_dao,
    get_upload_box_dao,
    get_work_package_dao,
)
from wps.adapters.outbound.http import AccessCheckAdapter
from wps.config import Config
from wps.core.repository import WorkPackageRepository
from wps.ports.inbound.repository import WorkPackageRepositoryPort

__all__ = ["Consumer", "prepare_consumer", "prepare_core", "prepare_rest_app"]


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
) -> AsyncGenerator[WorkPackageRepositoryPort]:
    """Constructs and initializes all core components with outbound dependencies."""
    async with (
        AccessCheckAdapter.construct(config=config) as download_access_checks,
        MongoDbDaoFactory.construct(config=config) as dao_factory,
    ):
        work_package_dao = await get_work_package_dao(
            config=config, dao_factory=dao_factory
        )
        dataset_dao = await get_dataset_dao(config=config, dao_factory=dao_factory)
        upload_box_dao = await get_upload_box_dao(
            config=config, dao_factory=dao_factory
        )
        accession_map_dao = await get_accession_map_dao(
            config=config, dao_factory=dao_factory
        )
        yield WorkPackageRepository(
            config=config,
            access_check=download_access_checks,
            dataset_dao=dataset_dao,
            upload_box_dao=upload_box_dao,
            work_package_dao=work_package_dao,
            accession_map_dao=accession_map_dao,
        )


def _prepare_core_with_override(
    *,
    config: Config,
    work_package_repo_override: WorkPackageRepositoryPort | None = None,
) -> AbstractAsyncContextManager[WorkPackageRepositoryPort]:
    """Get context manager for preparing the core components or provide override."""
    return (
        nullcontext(work_package_repo_override)
        if work_package_repo_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    work_package_repo_override: WorkPackageRepositoryPort | None = None,
) -> AsyncGenerator[FastAPI]:
    """Construct and initialize an REST API app along with all its dependencies.

    By default, the core dependencies are automatically prepared, but you can also
    provide them using the work_package_repo_override parameter.
    """
    app = get_configured_app(config=config)
    async with (
        _prepare_core_with_override(
            config=config, work_package_repo_override=work_package_repo_override
        ) as work_package_repo,
        GHGAAuthContextProvider.construct(
            config=config,
            context_class=AuthContext,
        ) as auth_context,
    ):
        app.dependency_overrides[dummies.auth_provider] = lambda: auth_context
        app.dependency_overrides[dummies.work_package_repo_port] = lambda: (
            work_package_repo
        )
        yield app


class Consumer(NamedTuple):
    """Container for an event subscriber and the repository that is used."""

    work_package_repository: WorkPackageRepositoryPort
    event_subscriber: KafkaEventSubscriber


@asynccontextmanager
async def prepare_consumer(
    *,
    config: Config,
    work_package_repo_override: WorkPackageRepositoryPort | None = None,
) -> AsyncGenerator[Consumer]:
    """Construct and initialize an event subscriber with all its dependencies.

    By default, the core dependencies are automatically prepared, but you can also
    provide them using the work_package_repo_override parameter.
    """
    async with _prepare_core_with_override(
        config=config, work_package_repo_override=work_package_repo_override
    ) as work_package_repository:
        event_sub_translator = EventSubTranslator(
            work_package_repository=work_package_repository,
            config=config,
        )
        rdub_outbox_translator = RDUBOutboxTranslator(
            config=config, work_package_repository=work_package_repository
        )
        accession_map_outbox_translator = AccessionMapOutboxTranslator(
            config=config, work_package_repository=work_package_repository
        )
        translator = ComboTranslator(
            translators=[
                event_sub_translator,
                rdub_outbox_translator,
                accession_map_outbox_translator,
            ]
        )

        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=translator,
                dlq_publisher=dlq_publisher,
            ) as event_subscriber,
        ):
            yield Consumer(work_package_repository, event_subscriber)
