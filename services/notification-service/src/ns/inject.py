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

"""DI functions."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext

from hexkit.providers.akafka.provider import KafkaEventPublisher, KafkaEventSubscriber
from hexkit.providers.mongodb.provider import MongoDbDaoFactory

from ns.adapters.inbound.event_sub import EventSubTranslator
from ns.adapters.outbound.dao import get_event_id_dao
from ns.adapters.outbound.smtp_client import SmtpClient
from ns.config import Config
from ns.core.notifier import Notifier
from ns.ports.inbound.notifier import NotifierPort


@asynccontextmanager
async def prepare_core(*, config: Config) -> AsyncGenerator[NotifierPort, None]:
    """Constructs and initializes all core components and their outbound dependencies."""
    smtp_client = SmtpClient(config=config)

    notifier = Notifier(config=config, smtp_client=smtp_client)
    yield notifier


def prepare_core_with_override(
    *, config: Config, notifier_override: NotifierPort | None = None
):
    """Resolve the notifier context manager based on config and override (if any)."""
    return (
        nullcontext(notifier_override)
        if notifier_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_event_subscriber(
    *,
    config: Config,
    notifier_override: NotifierPort | None = None,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Construct and initialize an event subscriber with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the notifier_override parameter.
    """
    async with (
        prepare_core_with_override(
            config=config, notifier_override=notifier_override
        ) as notifier,
        MongoDbDaoFactory.construct(config=config) as dao_factory,
    ):
        event_id_dao = await get_event_id_dao(dao_factory=dao_factory)
        event_sub_translator = EventSubTranslator(
            notifier=notifier,
            config=config,
            event_id_dao=event_id_dao,
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
