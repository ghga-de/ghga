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

"""
Module containing the main FastAPI router and (optionally) top-level API endpoints.

Additional endpoints might be structured in dedicated modules
(each of them having a sub-router).
"""

import logging

from ghga_service_commons.api import run_server
from hexkit.log import configure_logging
from hexkit.opentelemetry import configure_opentelemetry
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from rs.adapters.outbound.dao import get_box_dao, get_file_accession_mapping_dao
from rs.config import Config
from rs.inject import (
    get_persistent_publisher,
    prepare_event_subscriber,
    prepare_rest_app,
)

log = logging.getLogger(__name__)


async def run_rest_app():
    """Run the HTTP REST API."""
    config = Config()  # type: ignore [call-arg]
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)

    async with prepare_rest_app(config=config) as app:
        await run_server(app=app, config=config)


async def consume_events(run_forever: bool = True):
    """Run the event consumer"""
    config = Config()  # type: ignore[call-arg]
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)

    async with prepare_event_subscriber(config=config) as event_subscriber:
        await event_subscriber.run(forever=run_forever)


async def publish_events(*, all: bool = False):
    """Publish pending events. Set `--all` to (re)publish all events regardless of status."""
    config = Config()  # type: ignore[call-arg]
    configure_logging(config=config)
    configure_opentelemetry(service_name=config.service_name, config=config)

    log.info("Beginning manual event publish process")
    async with get_persistent_publisher(config=config) as persistent_publisher:
        if all:
            log.info("Republishing persistent events.")
            await persistent_publisher.republish()
        else:
            log.info("Publishing pending persistent events.")
            await persistent_publisher.publish_pending()

    async with MongoKafkaDaoPublisherFactory.construct(
        config=config
    ) as dao_publisher_factory:
        file_accession_publisher = await get_file_accession_mapping_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        box_dao = await get_box_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        if all:
            log.info("Republishing FileAccessionMappings...")
            await file_accession_publisher.republish()
            log.info("Republishing ResearchDataUploadBoxes...")
            await box_dao.republish()
        else:
            log.info("Publishing pending FileAccessionMappings...")
            await file_accession_publisher.publish_pending()
            log.info("Publishing pending ResearchDataUploadBoxes...")
            await box_dao.publish_pending()

    log.info("Manual event publish finished.")
