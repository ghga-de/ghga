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

"""Entrypoint of the package"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from ghga_service_commons.api import run_server
from ghga_service_commons.utils.utc_dates import assert_tz_is_utc
from hexkit.providers.akafka.provider import KafkaEventSubscriber

from auth_service.deps import get_mongodb_dao_factory
from auth_service.user_management.claims_repository.core.deletion import (
    DatasetDeletionHandler,
    DatasetDeletionPort,
)
from auth_service.user_management.claims_repository.deps import (
    ClaimDao,
    get_claim_dao_factory,
)
from auth_service.user_management.claims_repository.translators.akafka import (
    EventSubTranslator,
)

from .config import CONFIG, Config


async def get_claim_dao(
    config: Config,
) -> ClaimDao:
    """Get an event handler for dataset deletion events."""
    dao_factory = get_mongodb_dao_factory(config=config)
    claim_dao_factory = get_claim_dao_factory(config=config, dao_factory=dao_factory)
    return await claim_dao_factory.get_claim_dao()


@asynccontextmanager
async def prepare_event_handler(
    config: Config,
) -> AsyncGenerator[DatasetDeletionPort, None]:
    """Get an event handler for dataset deletion events."""
    claim_dao = await get_claim_dao(config)
    yield DatasetDeletionHandler(claim_dao=claim_dao)


@asynccontextmanager
async def prepare_event_subscriber(
    config: Config,
) -> AsyncGenerator[KafkaEventSubscriber, None]:
    """Get an event subscriber for dataset deletion events."""
    async with prepare_event_handler(config) as handler:
        translator = EventSubTranslator(config=config, handler=handler)
        async with KafkaEventSubscriber.construct(
            config=config, translator=translator
        ) as event_subscriber:
            yield event_subscriber


async def consume_events(config: Config = CONFIG):
    """Run an event consumer listening to the configured topic."""
    async with prepare_event_subscriber(config=config) as event_subscriber:
        await event_subscriber.run()


def run(config: Config = CONFIG):
    """Run the service"""
    assert_tz_is_utc()
    run_adapter = config.run_auth_adapter
    service = "auth_adapter" if run_adapter else "user_management"
    apis = config.include_apis
    consumer = not run_adapter and not apis
    mode = " and ".join(apis)
    mode = f"with {mode} API" if mode else "as event consumer"
    print(f"Starting {service} service {mode}")
    asyncio.run(
        consume_events(config=config)
        if consumer
        else run_server(app=f"auth_service.{service}.api.main:app", config=config)
    )


if __name__ == "__main__":
    run()
