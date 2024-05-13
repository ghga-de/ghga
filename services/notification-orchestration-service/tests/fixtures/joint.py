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

"""Bundle different test fixtures into one fixture"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from hexkit.custom_types import PytestScope
from hexkit.providers.akafka import KafkaEventSubscriber, KafkaOutboxSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from nos.config import Config
from nos.inject import prepare_core, prepare_event_subscriber, prepare_outbox_subscriber
from nos.ports.inbound.orchestrator import OrchestratorPort
from nos.ports.outbound.dao import UserDaoPort
from nos.translators.outbound.dao import user_dao_factory
from tests.fixtures.config import get_config


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    orchestrator: OrchestratorPort
    event_subscriber: KafkaEventSubscriber
    outbox_subscriber: KafkaOutboxSubscriber
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    user_dao: UserDaoPort


async def joint_fixture_function(
    mongodb: MongoDbFixture, kafka: KafkaFixture
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing

    **Do not call directly** Instead, use get_joint_fixture().
    """
    # merge configs from different sources with the default one:
    config = get_config(sources=[mongodb.config, kafka.config])

    # create a DI container instance:translators
    async with prepare_core(config=config) as orchestrator:
        async with (
            prepare_event_subscriber(
                config=config, core_override=orchestrator
            ) as event_subscriber,
            prepare_outbox_subscriber(
                config=config, core_override=orchestrator
            ) as outbox_subscriber,
        ):
            yield JointFixture(
                config=config,
                orchestrator=orchestrator,
                event_subscriber=event_subscriber,
                outbox_subscriber=outbox_subscriber,
                kafka=kafka,
                mongodb=mongodb,
                user_dao=await user_dao_factory(dao_factory=mongodb.dao_factory),
            )


def get_joint_fixture(scope: PytestScope = "function"):
    """Produce a joint fixture with desired scope"""
    return pytest_asyncio.fixture(joint_fixture_function, scope=scope)
