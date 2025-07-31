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
from hexkit.opentelemetry import configure_opentelemetry

from dcs.config import Config
from dcs.inject import (
    get_persistent_publisher,
    prepare_event_subscriber,
    prepare_outbox_cleaner,
    prepare_rest_app,
)
from dcs.migrations import run_db_migrations

DB_VERSION = 2


async def run_rest_app():
    """Run the HTTP REST API."""
    config = Config()
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)
    await run_db_migrations(config=config, target_version=DB_VERSION)

    async with prepare_rest_app(config=config) as app:
        await run_server(app=app, config=config)


async def consume_events(run_forever: bool = True):
    """Run an event consumer listening to the specified topics."""
    config = Config()
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)
    await run_db_migrations(config=config, target_version=DB_VERSION)

    async with prepare_event_subscriber(config=config) as event_subscriber:
        await event_subscriber.run(forever=run_forever)


async def run_outbox_cleanup():
    """Check if outbox buckets contains files that should be cleaned up and perform clean-up."""
    config = Config()
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)
    await run_db_migrations(config=config, target_version=DB_VERSION)

    async with prepare_outbox_cleaner(config=config) as cleanup_outbox:
        await cleanup_outbox


async def publish_events(*, all: bool = False):
    """Publish pending events. Set `--all` to (re)publish all events regardless of status."""
    config = Config()
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)
    await run_db_migrations(config=config, target_version=DB_VERSION)

    async with get_persistent_publisher(config=config) as persistent_publisher:
        if all:
            await persistent_publisher.republish()
        else:
            await persistent_publisher.publish_pending()
