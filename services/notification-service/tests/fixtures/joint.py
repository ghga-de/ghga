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
"""Bundle test fixtures into one fixture"""
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from hexkit.custom_types import PytestScope
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from ns.config import Config
from ns.inject import prepare_core, prepare_event_subscriber
from ns.ports.inbound.notifier import NotifierPort
from tests.fixtures.config import SMTP_TEST_CONFIG, get_config


@dataclass
class JointFixture:
    """Returned by joint_fixture_function"""

    config: Config
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    event_subscriber: KafkaEventSubscriber
    notifier: NotifierPort


async def joint_fixture_function(
    kafka_fixture: KafkaFixture,
    mongodb_fixture: MongoDbFixture,
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for integration testing"""
    # merge configs from different sources with the default one:
    config = get_config(
        sources=[kafka_fixture.config, mongodb_fixture.config, SMTP_TEST_CONFIG]
    )

    # prepare the core and the event subscriber
    async with prepare_core(config=config) as notifier:
        async with prepare_event_subscriber(
            config=config, notifier_override=notifier
        ) as event_subscriber:
            yield JointFixture(
                config=config,
                kafka=kafka_fixture,
                mongodb=mongodb_fixture,
                event_subscriber=event_subscriber,
                notifier=notifier,
            )


def get_joint_fixture(scope: PytestScope = "function"):
    """Produce a joint fixture with desired scope"""
    return pytest_asyncio.fixture(joint_fixture_function, scope=scope)
