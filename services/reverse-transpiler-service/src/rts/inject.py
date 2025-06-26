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

"""Module hosting the dependency injection logic."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from fastapi import FastAPI
from hexkit.providers.akafka.provider import (
    ComboTranslator,
    KafkaEventPublisher,
    KafkaEventSubscriber,
)
from hexkit.providers.mongodb import MongoDbDaoFactory

from rts.adapters.inbound.event_sub import OutboxSubTranslator
from rts.adapters.inbound.fastapi_ import dummies
from rts.adapters.inbound.fastapi_.configure import get_configured_app
from rts.adapters.outbound.dao import get_metadata_dao
from rts.config import Config
from rts.core.rev_tran import ReverseTranspiler
from rts.ports.inbound.rev_tran import ReverseTranspilerPort
from rts.ports.outbound.dao import MetadataDao


async def get_dao(*, config: Config) -> MetadataDao:
    """Constructs and initializes the DAO factory."""
    dao_factory = MongoDbDaoFactory(config=config)
    dao = await get_metadata_dao(dao_factory=dao_factory)
    return dao


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
    dao_override: MetadataDao | None = None,
) -> AsyncGenerator[ReverseTranspilerPort, None]:
    """Constructs and initializes all core components and their outbound dependencies.

    The _override parameters can be used to override the default dependencies.
    """
    dao = dao_override or await get_dao(config=config)
    yield ReverseTranspiler(config=config, dao=dao)


def prepare_core_with_override(
    *, config: Config, reverse_transpiler_override: ReverseTranspilerPort | None = None
):
    """Resolve the reverse_transpiler context manager based on config and override (if any)."""
    return (
        nullcontext(reverse_transpiler_override)
        if reverse_transpiler_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    reverse_transpiler_override: ReverseTranspilerPort | None = None,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the reverse_transpiler_override parameter.
    """
    app = get_configured_app(config=config)

    async with prepare_core_with_override(
        config=config, reverse_transpiler_override=reverse_transpiler_override
    ) as reverse_transpiler:
        app.dependency_overrides[dummies.reverse_transpiler_port] = (
            lambda: reverse_transpiler
        )
        yield app


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    reverse_transpiler_override: ReverseTranspilerPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the override parameter.
    """
    async with (
        prepare_core_with_override(
            config=config, reverse_transpiler_override=reverse_transpiler_override
        ) as reverse_transpiler,
        KafkaEventPublisher.construct(config=config) as dlq_publisher,
    ):
        _translator = OutboxSubTranslator(
            config=config, reverse_transpiler=reverse_transpiler
        )
        translator = ComboTranslator(translators=[_translator])
        async with KafkaEventSubscriber.construct(
            config=config, translator=translator, dlq_publisher=dlq_publisher
        ) as event_subscriber:
            yield event_subscriber
