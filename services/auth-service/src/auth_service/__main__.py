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
import importlib
import logging

from ghga_service_commons.api import run_server
from ghga_service_commons.utils.utc_dates import assert_tz_is_utc
from hexkit.log import configure_logging

from .config import CONFIG, Config

log = logging.getLogger(__name__)


def import_prepare_module(service: str):
    """Import the prepare module for the given service."""
    return importlib.import_module(f"auth_service.{service}.prepare")


async def consume_events(service: str, config: Config = CONFIG):
    """Run an event consumer listening to the configured topic."""
    prepare_event_subscriber = import_prepare_module(service).prepare_event_subscriber

    async with prepare_event_subscriber(config=config) as event_subscriber:
        await event_subscriber.run()


async def run_parallel(
    service: str, run_consumer: bool = False, config: Config = CONFIG
):
    """Run REST API(s) and consumer in parallel.

    When no API is specified, only the health endpoint will be available.
    """
    prepare_rest_app = import_prepare_module(service).prepare_rest_app

    async with prepare_rest_app(config=config) as app:
        service_runner = run_server(app=app, config=config)
        if run_consumer:
            event_consumer = consume_events(service=service, config=config)
            await asyncio.gather(service_runner, event_consumer)
        else:
            await service_runner


def run(config: Config = CONFIG):
    """Run the auth service"""
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
    log.info(f"Starting {service} service with {' and '.join(components)}")
    asyncio.run(run_parallel(service, run_consumer, config=config))


if __name__ == "__main__":
    run()
