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

from typing import AsyncGenerator, Optional, Union

from hexkit.providers.akafka.provider import KafkaEventPublisher
from hexkit.providers.akafka.testutils import KafkaFixture as BaseKafkaFixture
from kafka import KafkaAdminClient
from kafka.errors import KafkaError
from pytest_asyncio import fixture as async_fixture

from fixtures.config import Config

__all__ = ["kafka_fixture", "KafkaFixture"]


class KafkaFixture(BaseKafkaFixture):
    """An augmented Kafka fixture"""

    config: Config

    def delete_topics(self, topics: Optional[Union[str, list[str]]] = None):
        """Delete given topic(s) from Kafka broker.

        This process deletes the contained messages as the topics will be recreated
        by the default config.
        """
        if topics is None:
            topics = self.config.service_kafka_topics
        elif isinstance(topics, str):
            topics = [topics]
        admin_client = KafkaAdminClient(bootstrap_servers=self.kafka_servers)
        try:
            existing_topics = set(admin_client.list_topics())
            for topic in topics:
                if topic in existing_topics:
                    try:
                        admin_client.delete_topics([topic])
                    except KafkaError as error:
                        raise RuntimeError(
                            f"Could not delete topic {topic} from Kafka"
                        ) from error
        finally:
            admin_client.close()


@async_fixture(name="kafka")
async def kafka_fixture(config: Config) -> AsyncGenerator[KafkaFixture, None]:
    """Pytest fixture for tests depending on the Kafka-based provider."""

    async with KafkaEventPublisher.construct(config=config) as publisher:
        yield KafkaFixture(
            config=config, kafka_servers=config.kafka_servers, publisher=publisher
        )
