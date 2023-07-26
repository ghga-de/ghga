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

"""Fixture for testing code that uses the Kafka-based provider."""

from typing import AsyncGenerator

from hexkit.providers.akafka.provider import KafkaEventPublisher
from hexkit.providers.akafka.testutils import KafkaFixture
from pytest_asyncio import fixture as async_fixture

from fixtures.config import Config

__all__ = ["kafka_fixture", "KafkaFixture"]


@async_fixture(name="kafka", scope="session")
async def kafka_fixture(config: Config) -> AsyncGenerator[KafkaFixture, None]:
    """Pytest fixture for tests depending on the Kafka-based provider."""

    async with KafkaEventPublisher.construct(config=config) as publisher:
        yield KafkaFixture(
            config=config, kafka_servers=config.kafka_servers, publisher=publisher
        )
