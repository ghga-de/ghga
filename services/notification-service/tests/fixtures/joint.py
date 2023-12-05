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
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture, kafka_fixture  # noqa: F401

from ns.config import Config
from ns.inject import prepare_core, prepare_event_subscriber
from tests.fixtures.config import get_config


@dataclass
class JointFixture:
    """returned by joint_fixture"""

    config: Config
    kafka: KafkaFixture
    event_subscriber: KafkaEventSubscriber


@pytest_asyncio.fixture
async def joint_fixture(
    kafka_fixture: KafkaFixture,  # noqa: F811
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for integration testing"""
    # merge configs from different sources with the default one:
    config = get_config(sources=[kafka_fixture.config])

    # create a DI container instance:translators
    async with prepare_core(config=config) as notifier:
        async with prepare_event_subscriber(
            config=config, notifier_override=notifier
        ) as event_subscriber:
            yield JointFixture(
                config=config,
                kafka=kafka_fixture,
                event_subscriber=event_subscriber,
            )
