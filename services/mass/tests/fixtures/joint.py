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
from hexkit.custom_types import Ascii, JsonObject
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoClient, MongoDbFixture

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

    # the database is considered dirty if it is not (yet) populated properly
    database_dirty: bool
    # the events are considered dirty if some have been published already
    events_dirty: bool
    resources: dict[str, list[models.Resource]]


state = State(database_dirty=True, events_dirty=False, resources={})


@dataclass
class JointFixture:
    """A fixture embedding all other fixtures."""

    # attributes that can be used freely in tests

    config: Config
    resources: dict[str, list[models.Resource]]
    rest_client: AsyncTestClient

    # attributes that should not be accessed by tests directly

    _mongodb: MongoDbFixture
    _kafka: KafkaFixture
    _query_handler: QueryHandlerPort
    _event_subscriber: KafkaEventSubscriber

    # convenience methods that can be accessed by tests directly

    def purge_database(self) -> None:
        """Empty the database."""
        self._mongodb.empty_collections()
        state.database_dirty = True

    async def purge_events(self) -> None:
        """Purge all events."""
        await self._kafka.clear_topics()

    async def load_test_data(self) -> None:
        """Populate a collection for each file in test_data."""
        filename_pattern = re.compile(r"/(\w+)\.json")
        self._query_handler._dao_collection._indexes_created = False  # type: ignore
        for filename in glob.glob("tests/fixtures/test_data/*.json"):
            match_obj = re.search(filename_pattern, filename)
            if match_obj:
                collection_name = match_obj.group(1)
                resources = state.resources.get(collection_name)
                if resources is None:
                    resources = get_resources_from_file(filename)
                    state.resources[collection_name] = resources
                for resource in resources:
                    await self._query_handler.load_resource(
                        resource=resource, class_name=collection_name
                    )

    async def reset_state(self) -> None:
        """Reset the state of the database and event topics if needed."""
        if state.events_dirty:
            await self.purge_events()
            state.events_dirty = False
        if state.database_dirty:
            self.purge_database()
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

    @property
    def mongodb_client(self) -> MongoClient:
        """Get a MongoDB client and mark the database state as dirty."""
        state.database_dirty = True
        return self._mongodb.client

    def recreate_mongodb_indexes(self) -> None:
        """Set flag to recreate MongoDB indexes and mark the database state as dirty."""
        self._query_handler._dao_collection._indexes_created = False  # type: ignore
        state.database_dirty = True

    async def handle_query(
        self,
        class_name: str,
        query: str = "",
        filters: list[models.Filter] | None = None,
        sorting_parameters: list[models.SortingParameter] | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> models.QueryResults:
        """Handle a query."""
        return await self._query_handler.handle_query(
            class_name=class_name,
            query=query,
            filters=filters,
            skip=skip,
            limit=limit,
            sorting_parameters=sorting_parameters,
        )

    async def delete_resource(self, resource_id: str, class_name: str) -> None:
        """Delete a resource and mark the database state as dirty."""
        await self._query_handler.delete_resource(
            resource_id=resource_id, class_name=class_name
        )
        state.database_dirty = True

    async def load_resource(self, resource: models.Resource, class_name: str) -> None:
        """Load a resource and mark the database state as dirty."""
        await self._query_handler.load_resource(
            resource=resource, class_name=class_name
        )
        state.database_dirty = True

    async def consume_event(self) -> None:
        """Run the event subscriber in order to to consume an event."""
        await self._event_subscriber.run(forever=False)

    async def publish_event(
        self, payload: JsonObject, type_: Ascii, topic: Ascii, key: Ascii = "test"
    ) -> None:
        """Publish a test event and mark the events state as dirty."""
        await self._kafka.publish_event(
            payload=payload, type_=type_, topic=topic, key=key
        )
        state.events_dirty = True


@pytest_asyncio.fixture()
async def joint_fixture(
    mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[JointFixture, None]:
    """Function scoped joint fixture for API-level integration testing."""
    # merge configs from different sources with the default one:
    config = get_config(sources=[mongodb.config, kafka.config], kafka_enable_dlq=True)

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
            _query_handler=query_handler,
            _event_subscriber=event_subscriber,
            _kafka=kafka,
            _mongodb=mongodb,
            rest_client=rest_client,
            resources=state.resources,
        )
        await joint_fixture.reset_state()
        yield joint_fixture
