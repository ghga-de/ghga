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

"""Fixture for testing code that uses the Kafka-based provider."""

from collections.abc import AsyncGenerator

from aiokafka.admin import AIOKafkaAdminClient
from hexkit.providers.akafka.provider import KafkaEventPublisher
from hexkit.providers.akafka.testutils import KafkaFixture as BaseKafkaFixture
from pytest_asyncio import fixture as async_fixture

from fixtures.config import Config

__all__ = ["kafka_fixture", "KafkaFixture"]


def wrapped_exec_run(command: str, run_in_shell: bool):
    """Wrap command execution for use inside docker container.

    Since we cannot do this easily in the docker compose environment,
    we raise an error to make sure features that depend on this are not used.
    """
    raise NotImplementedError("Not possible to wrap a command for Kafka.")


class KafkaFixture(BaseKafkaFixture):
    """A Kafka fixture that allows deletion of topics."""

    async def delete_topics(
        self,
        topics: str | list[str] | None = None,
        exclude_internal: bool = True,
    ):
        """Clear the given topics by deleting them completely."""
        admin_client = AIOKafkaAdminClient(bootstrap_servers=self.kafka_servers)
        await admin_client.start()
        try:
            if topics is None:
                topics = await admin_client.list_topics()
            elif isinstance(topics, str):
                topics = [topics]
            if exclude_internal:
                topics = [topic for topic in topics if not topic.startswith("__")]
            await admin_client.delete_topics(topics, timeout_ms=10000)
        finally:
            await admin_client.close()


@async_fixture(name="kafka", scope="session")
async def kafka_fixture(config: Config) -> AsyncGenerator[KafkaFixture, None]:
    """Pytest fixture for tests depending on the Kafka-based provider."""
    async with KafkaEventPublisher.construct(config=config) as publisher:
        yield KafkaFixture(
            config=config,
            kafka_servers=config.kafka_servers,
            publisher=publisher,
            cmd_exec_func=wrapped_exec_run,
        )
