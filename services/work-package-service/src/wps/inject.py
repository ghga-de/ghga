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
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import NamedTuple

from fastapi import FastAPI
from ghga_service_commons.auth.ghga import AuthContext, GHGAAuthContextProvider
from ghga_service_commons.utils.context import asyncnullcontext
from hexkit.providers.akafka import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb import MongoDbDaoFactory

from wps.adapters.inbound.event_sub import EventSubTranslator
from wps.adapters.inbound.fastapi_ import dummies
from wps.adapters.inbound.fastapi_.configure import get_configured_app
from wps.adapters.outbound.dao import DatasetDaoConstructor, WorkPackageDaoConstructor
from wps.adapters.outbound.http import AccessCheckAdapter
from wps.config import Config
from wps.core.repository import WorkPackageRepository
from wps.ports.inbound.repository import WorkPackageRepositoryPort

__all__ = ["Consumer", "prepare_consumer", "prepare_core", "prepare_rest_app"]


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
) -> AsyncGenerator[WorkPackageRepositoryPort, None]:
    """Constructs and initializes all core components with outbound dependencies."""
    dao_factory = MongoDbDaoFactory(config=config)
    work_package_dao = await WorkPackageDaoConstructor.construct(
        config=config,
        dao_factory=dao_factory,
    )
    dataset_dao = await DatasetDaoConstructor.construct(
        config=config,
        dao_factory=dao_factory,
    )
    async with AccessCheckAdapter.construct(config=config) as download_access_checks:
        yield WorkPackageRepository(
            config=config,
            access_check=download_access_checks,
            dataset_dao=dataset_dao,
            work_package_dao=work_package_dao,
        )


def _prepare_core_with_override(
    *,
    config: Config,
    work_package_repo_override: WorkPackageRepositoryPort | None = None,
) -> AbstractAsyncContextManager[WorkPackageRepositoryPort]:
    """Get context manager for preparing the core components or provide override."""
    return (
        asyncnullcontext(work_package_repo_override)
        if work_package_repo_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    work_package_repo_override: WorkPackageRepositoryPort | None = None,
) -> AsyncGenerator[FastAPI, None]:
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
        app.dependency_overrides[dummies.work_package_repo_port] = (
            lambda: work_package_repo
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
) -> AsyncGenerator[Consumer, None]:
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

        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=event_sub_translator,
                dlq_publisher=dlq_publisher,
            ) as event_subscriber,
        ):
            yield Consumer(work_package_repository, event_subscriber)
