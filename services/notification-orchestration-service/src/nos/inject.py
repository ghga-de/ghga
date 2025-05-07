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
"""Module hosting the dependency injection framework."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from hexkit.providers.akafka import (
    ComboTranslator,
    KafkaEventPublisher,
    KafkaEventSubscriber,
)
from hexkit.providers.mongodb import MongoDbDaoFactory

from nos.config import Config
from nos.core.orchestrator import Orchestrator
from nos.ports.inbound.orchestrator import OrchestratorPort
from nos.translators.inbound.event_sub import (
    AccessRequestOutboxTranslator,
    EventSubTranslator,
    UserOutboxTranslator,
)
from nos.translators.outbound.dao import get_access_request_dao, get_user_dao
from nos.translators.outbound.event_pub import NotificationEmitter


@asynccontextmanager
async def prepare_core(
    *,
    config: Config,
) -> AsyncGenerator[OrchestratorPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    dao_factory = MongoDbDaoFactory(config=config)
    user_dao = await get_user_dao(dao_factory=dao_factory)
    access_request_dao = await get_access_request_dao(dao_factory=dao_factory)

    async with KafkaEventPublisher.construct(config=config) as event_publisher:
        notification_emitter = NotificationEmitter(
            config=config, event_publisher=event_publisher
        )
        yield Orchestrator(
            notification_emitter=notification_emitter,
            access_request_dao=access_request_dao,
            user_dao=user_dao,
            config=config,
        )


def prepare_core_with_override(
    *,
    config: Config,
    core_override: OrchestratorPort | None = None,
):
    """Resolve the prepare_core context manager based on config and override (if any)."""
    return nullcontext(core_override) if core_override else prepare_core(config=config)


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    core_override: OrchestratorPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the override parameter.
    """
    async with prepare_core_with_override(
        config=config, core_override=core_override
    ) as orchestrator:
        event_sub_translator = EventSubTranslator(
            orchestrator=orchestrator,
            config=config,
        )
        access_request_outbox_translator = AccessRequestOutboxTranslator(
            config=config,
            orchestrator=orchestrator,
        )
        user_outbox_translator = UserOutboxTranslator(
            orchestrator=orchestrator,
            config=config,
        )
        combo_translator = ComboTranslator(
            translators=[
                event_sub_translator,
                access_request_outbox_translator,
                user_outbox_translator,
            ]
        )

        async with (
            KafkaEventPublisher.construct(config=config) as dlq_publisher,
            KafkaEventSubscriber.construct(
                config=config,
                translator=combo_translator,
                dlq_publisher=dlq_publisher,
            ) as event_subscriber,
        ):
            yield event_subscriber
