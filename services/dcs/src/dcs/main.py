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

"""In this module object construction and dependency injection is carried out."""

from ghga_service_commons.api import run_server
from hexkit.log import configure_logging

from dcs.config import Config
from dcs.inject import (
    prepare_event_subscriber,
    prepare_outbox_cleaner,
    prepare_rest_app,
)


async def run_rest_app():
    """Run the HTTP REST API."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    async with prepare_rest_app(config=config) as app:
        await run_server(app=app, config=config)


async def consume_events(run_forever: bool = True):
    """Run an event consumer listening to the specified topic."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    async with prepare_event_subscriber(config=config) as event_subscriber:
        await event_subscriber.run(forever=run_forever)


async def run_outbox_cleanup():
    """Check if outbox buckets contains files that should be cleaned up and perform clean-up."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    async with prepare_outbox_cleaner(config=config) as cleanup_outbox:
        await cleanup_outbox
