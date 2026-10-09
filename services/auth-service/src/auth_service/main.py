# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Entrypoints to prepare and run the application."""

import importlib
import logging

from auth_service.config import Config
from auth_service.migrations import MIGRATION_MAP
from ghga_service_commons.api import run_server
from hexkit.log import configure_logging
from hexkit.opentelemetry import configure_opentelemetry
from hexkit.providers.mongodb.migrations import MigrationManager, check_db_version

log = logging.getLogger(__name__)

DB_VERSION = 2


def import_prepare_module(auth_adapter: bool):
    """Import the prepare module of the auth adapter or of the auth service.

    Only the module of the service being run may be imported: the auth service's
    routers check at import that the configured key is a public one, while the
    auth adapter is configured with the private key.
    """
    package = "auth_service.auth_adapter" if auth_adapter else "auth_service"
    return importlib.import_module(f"{package}.prepare")


async def run_rest_app() -> None:
    """Run the HTTP REST APIs set in `provide_apis`."""
    config = Config()
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)
    apis = config.provide_apis
    if not apis:
        raise ValueError("provide_apis must name at least one API")
    auth_adapter = "ext_auth" in apis
    if auth_adapter and len(apis) > 1:
        raise ValueError("ext_auth cannot be combined with other APIs")
    log.info("Starting the %s API", " and ".join(apis))
    await check_db_version(config=config, target_version=DB_VERSION)

    prepare_rest_app = import_prepare_module(auth_adapter).prepare_rest_app
    async with prepare_rest_app(config=config) as app:
        await run_server(app=app, config=config)


async def consume_events(run_forever: bool = True) -> None:
    """Run an event consumer listening to the configured topic."""
    config = Config()
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)
    await check_db_version(config=config, target_version=DB_VERSION)

    prepare_event_subscriber = import_prepare_module(
        auth_adapter=False
    ).prepare_event_subscriber
    async with prepare_event_subscriber(config=config) as event_subscriber:
        await event_subscriber.run(forever=run_forever)


async def migrate_db() -> None:
    """Run database migrations as a one-off command."""
    config = Config()
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)
    async with MigrationManager(
        config=config, target_version=DB_VERSION, migration_map=MIGRATION_MAP
    ) as mm:
        await mm.migrate_or_wait()
