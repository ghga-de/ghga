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

"""
Module containing the main FastAPI router and (optionally) top-level API endpoints.

Additional endpoints might be structured in dedicated modules
(each of them having a sub-router).
"""

from ghga_service_commons.api import run_server
from hexkit.log import configure_logging

from rts.config import Config
from rts.inject import prepare_event_subscriber, prepare_rest_app
from rts.migrations.entry import run_db_migrations

DB_VERSION = 2


async def run_rest_app():
    """Run the HTTP REST API."""
    config = Config()  # type: ignore [call-arg]
    configure_logging(config=config)

    async with prepare_rest_app(config=config) as app:
        await run_server(app=app, config=config)


async def consume_events(run_forever: bool = True):
    """Run the event consumer"""
    config = Config()  # type: ignore[call-arg]
    configure_logging(config=config)

    async with prepare_event_subscriber(config=config) as event_subscriber:
        await event_subscriber.run(forever=run_forever)


async def migrate_db() -> None:
    """Run database migrations as a one-off command."""
    config = Config()  # type: ignore
    configure_logging(config=config)
    await run_db_migrations(config=config, target_version=DB_VERSION)
