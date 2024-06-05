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

"""Module hosting the dependency injection container."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from ghga_service_commons.utils.context import asyncnullcontext
from hexkit.providers.akafka.provider import KafkaEventPublisher

from fis.adapters.inbound.fastapi_ import dummies
from fis.adapters.inbound.fastapi_.configure import get_configured_app
from fis.adapters.outbound.event_pub import EventPubTranslator
from fis.adapters.outbound.vault import VaultAdapter
from fis.config import Config
from fis.core.ingest import LegacyUploadMetadataProcessor, UploadMetadataProcessor
from fis.ports.inbound.ingest import (
    LegacyUploadMetadataProcessorPort,
    UploadMetadataProcessorPort,
)


@asynccontextmanager
async def prepare_core(
    *, config: Config
) -> AsyncGenerator[
    tuple[UploadMetadataProcessorPort, LegacyUploadMetadataProcessorPort], None
]:
    """Constructs and initializes all core components and their outbound dependencies."""
    vault_adapter = VaultAdapter(config=config)
    async with KafkaEventPublisher.construct(config=config) as event_pub_provider:
        event_publisher = EventPubTranslator(config=config, provider=event_pub_provider)
        yield (
            UploadMetadataProcessor(
                config=config,
                event_publisher=event_publisher,
                vault_adapter=vault_adapter,
            ),
            LegacyUploadMetadataProcessor(
                config=config,
                event_publisher=event_publisher,
                vault_adapter=vault_adapter,
            ),
        )


def prepare_core_with_override(
    *,
    config: Config,
    core_override: tuple[UploadMetadataProcessorPort, LegacyUploadMetadataProcessorPort]
    | None = None,
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
    core_override: tuple[UploadMetadataProcessorPort, LegacyUploadMetadataProcessorPort]
    | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize a REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as (
        upload_metadata_processor,
        legacy_upload_metadata_processor,
    ):
        app.dependency_overrides[dummies.config_dummy] = lambda: config

        app.dependency_overrides[dummies.upload_processor_port] = (
            lambda: upload_metadata_processor
        )

        app.dependency_overrides[dummies.legacy_upload_processor] = (
            lambda: legacy_upload_metadata_processor
        )

        yield app
