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
"""Defines fixtures for the tests"""
import pytest
from hexkit.providers.akafka.testutils import KafkaFixture, get_kafka_fixture
from hexkit.providers.mongodb.testutils import MongoDbFixture, get_mongodb_fixture

from tests.fixtures.joint import get_joint_fixture

kafka_fixture = get_kafka_fixture(scope="session")
mongodb_fixture = get_mongodb_fixture(scope="session")
joint_fixture = get_joint_fixture(scope="session")


@pytest.fixture(autouse=True, scope="function")
def reset_state(mongodb_fixture: MongoDbFixture, kafka_fixture: KafkaFixture):
    """Reset the state of the system before each test"""
    mongodb_fixture.empty_collections()
    kafka_fixture.clear_topics()
