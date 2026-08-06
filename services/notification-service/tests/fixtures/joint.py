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
#
"""Bundle test fixtures into one fixture"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from ns.config import Config
from ns.inject import prepare_core, prepare_event_subscriber
from ns.ports.inbound.notifier import NotifierPort
from tests.fixtures.config import SMTP_TEST_CONFIG, get_config
from tests.fixtures.lox24 import Lox24Mock


@dataclass
class JointFixture:
    """Returned by joint_fixture"""

    config: Config
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    event_subscriber: KafkaEventSubscriber
    notifier: NotifierPort
    lox24: Lox24Mock


@pytest_asyncio.fixture()
async def joint_fixture(
    request,
    kafka: KafkaFixture,
    mongodb: MongoDbFixture,
    lox24: Lox24Mock,
) -> AsyncGenerator[JointFixture]:
    """A fixture that embeds all other fixtures for integration testing"""
    # merge configs from different sources with the default one:
    config = get_config(sources=[kafka.config, mongodb.config, SMTP_TEST_CONFIG])
    # prepare the core and the event subscriber, with the SMS gateway mocked out
    async with (
        prepare_core(
            config=config, sms_transport_override=lox24.as_transport()
        ) as notifier,
        prepare_event_subscriber(
            config=config, notifier_override=notifier
        ) as event_subscriber,
    ):
        yield JointFixture(
            config=config,
            kafka=kafka,
            mongodb=mongodb,
            event_subscriber=event_subscriber,
            notifier=notifier,
            lox24=lox24,
        )
