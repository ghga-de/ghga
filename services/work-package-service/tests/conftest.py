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

"""Shared fixtures"""

import asyncio
from time import sleep

import pytest
from hexkit.providers.akafka.testutils import KafkaFixture, get_kafka_fixture
from hexkit.providers.mongodb.testutils import MongoDbFixture, get_mongodb_fixture

from tests.fixtures.datasets import DATASET_UPSERTION_EVENT

kafka_fixture = get_kafka_fixture("session")
mongodb_fixture = get_mongodb_fixture("session")


@pytest.fixture(autouse=True, scope="function")
def reset_db(mongodb_fixture: MongoDbFixture):
    """Clear the database before tests."""
    mongodb_fixture.empty_collections()


@pytest.fixture(scope="function")
def populate_db(reset_db, consumer, config, kafka_fixture: KafkaFixture):
    """Populate the database

    Required for tests using the consumer or client fixtures.
    """
    loop = asyncio.get_event_loop()
    # publish an event announcing a dataset
    loop.run_until_complete(
        kafka_fixture.publish_event(
            payload=DATASET_UPSERTION_EVENT.model_dump(),
            topic=config.dataset_change_event_topic,
            type_=config.dataset_upsertion_event_type,
            key="test-key-fixture",
        )
    )
    # wait for event to be submitted and processed,
    # so that the database is populated with the published datasets
    loop.run_until_complete(
        asyncio.wait_for(consumer.event_subscriber.run(forever=False), timeout=10)
    )
    sleep(0.25)
