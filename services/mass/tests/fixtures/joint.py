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
#

"""Provides multiple fixtures in one spot, with a mongodb fixture that comes pre-populated"""

import glob
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.custom_types import JsonObject
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from mass.config import Config
from mass.core import models
from mass.inject import prepare_core, prepare_event_subscriber, prepare_rest_app
from mass.ports.inbound.query_handler import QueryHandlerPort
from tests.fixtures.config import get_config
from tests.fixtures.utils import get_resources_from_file


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    query_handler: QueryHandlerPort
    event_subscriber: KafkaEventSubscriber
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    rest_client: AsyncTestClient

    def remove_db_data(self) -> None:
        """Delete everything in the database to start from a clean slate"""
        self.mongodb.empty_collections()

    async def load_test_data(self) -> None:
        """Populate a collection for each file in test_data"""
        filename_pattern = re.compile(r"/(\w+)\.json")
        self.query_handler._dao_collection._indexes_created = False  # type: ignore
        for filename in glob.glob("tests/fixtures/test_data/*.json"):
            match_obj = re.search(filename_pattern, filename)
            if match_obj:
                collection_name = match_obj.group(1)
                resources = get_resources_from_file(filename)
                for resource in resources:
                    await self.query_handler.load_resource(
                        resource=resource, class_name=collection_name
                    )

    async def call_search_endpoint(
        self, search_parameters: JsonObject
    ) -> models.QueryResults:
        """Convenience function to call the /rpc/search endpoint"""
        response = await self.rest_client.post(
            url="/rpc/search", json=search_parameters
        )
        response.raise_for_status()
        return models.QueryResults(**response.json())


@pytest_asyncio.fixture
async def joint_fixture(
    mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing."""
    # merge configs from different sources with the default one:
    config = get_config(sources=[mongodb.config, kafka.config])

    async with (
        prepare_core(config=config) as query_handler,
        prepare_rest_app(config=config, query_handler_override=query_handler) as app,
        prepare_event_subscriber(
            config=config, query_handler_override=query_handler
        ) as event_subscriber,
        AsyncTestClient(app=app) as rest_client,
    ):
        joint_fixture = JointFixture(
            config=config,
            query_handler=query_handler,
            event_subscriber=event_subscriber,
            kafka=kafka,
            mongodb=mongodb,
            rest_client=rest_client,
        )
        await joint_fixture.load_test_data()
        yield joint_fixture
