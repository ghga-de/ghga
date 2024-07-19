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

"""Entrypoint of the package"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from ghga_service_commons.api import run_server
from ghga_service_commons.utils.utc_dates import assert_tz_is_utc
from hexkit.log import configure_logging
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
from auth_service.user_management.claims_repository.translators.event_sub import (
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


async def run_parallel(
    service: str, run_consumer: bool = False, config: Config = CONFIG
):
    """Run REST API(s) and consumer in parallel.

    When no API is specified, only the health endpoint will be available.
    """
    service_runner = run_server(
        app=f"auth_service.{service}.api.main:app", config=config
    )
    if run_consumer:
        await asyncio.gather(service_runner, consume_events(config=config))
    else:
        await service_runner


def run(config: Config = CONFIG):
    """Run the service"""
    configure_logging(config=config)
    assert_tz_is_utc()
    apis = config.provide_apis
    run_consumer = config.run_consumer
    ext_auth = "ext_auth" in apis
    if ext_auth and len(apis) > 1:
        raise ValueError("ext_auth cannot be combined with other APIs")
    service = "auth_adapter" if ext_auth else "user_management"
    components = [f"{api} API" for api in apis]
    if run_consumer:
        components.append("event consumer")
    if not components:
        raise ValueError("must specify an API or run as event consumer")
    print(f"Starting {service} service with {' and '.join(components)}")
    asyncio.run(run_parallel(service, run_consumer, config=config))


if __name__ == "__main__":
    run()
