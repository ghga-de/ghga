# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from typing import Optional

from fastapi import FastAPI
from ghga_service_commons.utils.context import asyncnullcontext
from hexkit.providers.akafka import KafkaEventPublisher

from pcs.adapters.inbound.fastapi_ import dummies
from pcs.adapters.inbound.fastapi_.configure import get_configured_app
from pcs.adapters.outbound.event_pub import EventPubTranslator
from pcs.config import Config
from pcs.core.file_deletion import FileDeletion
from pcs.ports.inbound.file_deletion import FileDeletionPort


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[FileDeletionPort, None]:
    """Construct and initialize the core component and its outbound dependencies."""
    async with KafkaEventPublisher.construct(config=config) as event_pub_provider:
        event_publisher = EventPubTranslator(config=config, provider=event_pub_provider)
        file_deletion = FileDeletion(event_publisher=event_publisher)
        yield file_deletion


def prepare_core_with_override(
    *,
    config: Config,
    core_override: Optional[FileDeletionPort] = None,
):
    """Return a context manager for preparing the core that can be overwritten
    with the given value.
    """
    return (
        asyncnullcontext(core_override)
        if core_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    core_override: Optional[FileDeletionPort] = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the core_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as file_deletion:
        app.dependency_overrides[dummies.token_hash_config] = lambda: config
        app.dependency_overrides[dummies.file_deletion] = lambda: file_deletion
        yield app
