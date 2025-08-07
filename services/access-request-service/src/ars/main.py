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

"""In this module object construction and dependency injection is carried out."""

from ghga_service_commons.api import run_server
from hexkit.log import configure_logging

from ars.config import Config
from ars.migrations import run_db_migrations
from ars.prepare import prepare_access_request_dao, prepare_consumer, prepare_rest_app

DB_VERSION = 3


async def run_rest_app():
    """Run the HTTP REST API."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    await run_db_migrations(config=config, target_version=DB_VERSION)

    async with prepare_rest_app(config=config) as app:
        await run_server(app=app, config=config)


async def consume_events(run_forever: bool = True) -> None:
    """Run an event consumer listening to the configured topic."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    await run_db_migrations(config=config, target_version=DB_VERSION)

    async with prepare_consumer(config=config) as consumer:
        await consumer.event_subscriber.run(forever=run_forever)


async def publish_events(*, all: bool = False):
    """Publish pending events. Set `--all` to (re)publish all events regardless of status."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    await run_db_migrations(config=config, target_version=DB_VERSION)

    async with prepare_access_request_dao(config=config) as outbox_publisher:
        if all:
            await outbox_publisher.republish()
        else:
            await outbox_publisher.publish_pending()
