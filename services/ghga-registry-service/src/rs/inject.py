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

"""Dependency injection and setup of main components"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from ghga_service_commons.auth.jwt_auth import JWTAuthConfig, JWTAuthContextProvider
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from rs.adapters.inbound.fastapi_ import dummies
from rs.adapters.inbound.fastapi_.configure import get_configured_app
from rs.adapters.inbound.fastapi_.rest_models import MapFileIdsWorkOrder
from rs.adapters.outbound.dao import get_alt_accession_dao
from rs.config import Config
from rs.constants import AUTH_CHECK_CLAIMS
from rs.core.files import FileController
from rs.ports.inbound.files import FileControllerPort

__all__ = [
    "prepare_core",
    "prepare_rest_app",
]


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[FileControllerPort]:
    """Constructs and initializes all core components and their outbound dependencies."""
    async with (
        MongoKafkaDaoPublisherFactory.construct(config=config) as dao_publisher_factory,
        get_alt_accession_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        ) as alt_accession_dao,
    ):
        yield FileController(alt_accession_dao=alt_accession_dao)


def prepare_core_with_override(
    *,
    config: Config,
    core_override: FileControllerPort | None = None,
):
    """Resolve the core class context manager based on config and override (if any)."""
    return nullcontext(core_override) if core_override else prepare_core(config=config)


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    core_override: FileControllerPort | None = None,
) -> AsyncGenerator[FastAPI]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as core_class:
        app.dependency_overrides[dummies.file_controller_port] = lambda: core_class
        auth_config = JWTAuthConfig(
            auth_key=config.uos_auth_config.auth_key,
            auth_check_claims=dict.fromkeys(AUTH_CHECK_CLAIMS),
        )
        provider = JWTAuthContextProvider(
            config=auth_config, context_class=MapFileIdsWorkOrder
        )
        app.dependency_overrides[dummies.auth_provider_dummy] = lambda: provider
        yield app
