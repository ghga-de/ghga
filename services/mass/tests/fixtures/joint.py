# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
# pylint: disable=unused-import, redefined-outer-name

import glob
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.custom_types import JsonObject
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from pytest_asyncio.plugin import _ScopeName

from mass.config import Config
from mass.container import Container
from mass.core import models
from mass.main import get_configured_container, get_rest_api
from tests.fixtures.config import get_config
from tests.fixtures.utils import get_resources_from_file


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    container: Container
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    rest_client: AsyncTestClient

    def remove_db_data(self) -> None:
        """Delete everything in the database to start from a clean slate"""
        self.mongodb.empty_collections()

    async def load_test_data(self) -> None:
        """Populate a collection for each file in test_data"""
        filename_pattern = re.compile(r"/(\w+)\.json")
        query_handler = await self.container.query_handler()
        query_handler._dao_collection._indexes_created = (
            False  # pylint: disable=protected-access
        )
        for filename in glob.glob("tests/fixtures/test_data/*.json"):
            match_obj = re.search(filename_pattern, filename)
            if match_obj:
                collection_name = match_obj.group(1)
                resources = get_resources_from_file(filename)
                for resource in resources:
                    await query_handler.load_resource(
                        resource=resource, class_name=collection_name
                    )

    async def call_search_endpoint(
        self, search_parameters: JsonObject
    ) -> models.QueryResults:
        """Convenience function to call the /rpc/search endpoint"""
        response = await self.rest_client.post(
            url="/rpc/search", json=search_parameters
        )
        results = models.QueryResults(**response.json())
        return results


async def joint_fixture_function(
    mongodb_fixture: MongoDbFixture, kafka_fixture: KafkaFixture
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing

    **Do not call directly** Instead, use get_joint_fixture().
    """
    # merge configs from different sources with the default one:
    config = get_config(sources=[mongodb_fixture.config, kafka_fixture.config])

    # create a DI container instance:translators
    async with get_configured_container(config=config) as container:
        # setup an API test client:
        api = get_rest_api(config=config)
        async with AsyncTestClient(app=api) as rest_client:
            yield JointFixture(
                config=config,
                container=container,
                kafka=kafka_fixture,
                mongodb=mongodb_fixture,
                rest_client=rest_client,
            )


def get_joint_fixture(scope: _ScopeName = "function"):
    """Produce a joint fixture with desired scope"""
    return pytest_asyncio.fixture(joint_fixture_function, scope=scope)
