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
from collections.abc import AsyncGenerator, Mapping
from dataclasses import dataclass
from typing import TypeAlias

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from mass.config import Config
from mass.core import models
from mass.inject import prepare_core, prepare_event_subscriber, prepare_rest_app
from mass.ports.inbound.query_handler import QueryHandlerPort
from tests.fixtures.config import get_config
from tests.fixtures.utils import get_resources_from_file

QueryParams: TypeAlias = Mapping[str, int | str | list[str]]


@dataclass
class State:
    """The current state of the database and the event topics"""

    database_dirty: bool
    events_dirty: bool
    resources: dict[str, list[models.Resource]]


state = State(database_dirty=True, events_dirty=True, resources={})


@dataclass
class JointFixture:
    """A fixture embedding all other fixtures."""

    config: Config
    query_handler: QueryHandlerPort
    mongodb: MongoDbFixture
    kafka: KafkaFixture
    rest_client: AsyncTestClient
    event_subscriber: KafkaEventSubscriber
    resources: dict[str, list[models.Resource]]

    def empty_database(self) -> None:
        """Empty the database."""
        self.mongodb.empty_collections()
        state.database_dirty = True

    async def load_test_data(self) -> None:
        """Populate a collection for each file in test_data."""
        filename_pattern = re.compile(r"/(\w+)\.json")
        self.query_handler._dao_collection._indexes_created = False  # type: ignore
        for filename in glob.glob("tests/fixtures/test_data/*.json"):
            match_obj = re.search(filename_pattern, filename)
            if match_obj:
                collection_name = match_obj.group(1)
                resources = state.resources.get(collection_name)
                if resources is None:
                    resources = get_resources_from_file(filename)
                    state.resources[collection_name] = resources
                for resource in resources:
                    await self.query_handler.load_resource(
                        resource=resource, class_name=collection_name
                    )

    async def reset_state(self) -> None:
        """Reset the state of the database and event topics if needed."""
        if state.events_dirty:
            await self.kafka.clear_topics()
            state.events_dirty = False
        if state.database_dirty:
            self.mongodb.empty_collections()
            await self.load_test_data()
            state.database_dirty = False

    async def call_search_endpoint(self, params: QueryParams) -> models.QueryResults:
        """Call the search endpoint (convenience method)."""
        response = await self.rest_client.get(url="/search", params=params)
        result = response.json()
        assert result is not None, result
        assert "detail" in result or "hits" in result, result
        response.raise_for_status()
        return models.QueryResults(**result)

    async def delete_resource(self, resource_id: str, class_name: str) -> None:
        """Delete a resource and mark the database as dirty."""
        await self.query_handler.delete_resource(
            resource_id=resource_id, class_name=class_name
        )
        state.database_dirty = True

    async def load_resource(self, resource: models.Resource, class_name: str) -> None:
        """Load a resource and mark the database as dirty."""
        await self.query_handler.load_resource(resource=resource, class_name=class_name)
        state.database_dirty = True


@pytest_asyncio.fixture()
async def joint_fixture(
    mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[JointFixture, None]:
    """Function scoped joint fixture for API-level integration testing."""
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
            resources=state.resources,
        )
        await joint_fixture.reset_state()
        yield joint_fixture
