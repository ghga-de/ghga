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

"""Common fixtures for integration tests."""

from collections.abc import AsyncGenerator, Generator
from typing import Any, Self

import pytest
import pytest_asyncio
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.akafka.provider import KafkaEventPublisher
from hexkit.providers.akafka.testcontainer import DEFAULT_IMAGE as KAFKA_IMAGE
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.provider import MongoDbDaoFactory
from hexkit.providers.mongodb.testutils import (
    MongoDbFixture,
    config_from_mongodb_container,
)
from testcontainers.kafka import KafkaContainer
from testcontainers.mongodb import MongoDbContainer

# Note: We do not use get_kafka_fixture() and get_mongodb_fixture() from hexutils here,
# because this does not allow to run container creation and event publisher creation
# in different scopes. This is particularly important because the event loops are tied
# to the scopes of the fixtures. TODO: Put this code in hexkit and import it here.


class KafkaContainerFixture(KafkaContainer):
    """Kafka container with config and command execution."""

    kafka_config: KafkaConfig

    def __init__(self, port: int = 9093, **kwargs: Any) -> None:
        """Initialize the container."""
        super().__init__(image=KAFKA_IMAGE, port=port, **kwargs)

    def __enter__(self) -> Self:
        """Enter the container context."""
        super().__enter__()
        kafka_servers = [self.get_bootstrap_server()]
        self.kafka_config = KafkaConfig(
            service_name="test_publisher",
            service_instance_id="001",
            kafka_servers=kafka_servers,
        )
        return self

    def wrapped_exec_run(self, command: str, run_in_shell: bool):
        """Run the given command in the kafka testcontainer.

        Args:
            - `command`: The full command to run.
            - `run_in_shell`: If True, will run the command in a shell.

        Raises:
            - `RuntimeError`: when the exit code returned by the command is not zero.
        """
        cmd = ["sh", "-c", command] if run_in_shell else command
        exit_code, output = self.get_wrapped_container().exec_run(cmd)

        if exit_code != 0:
            raise RuntimeError(f"result: {exit_code}, output: {output.decode('utf-8')}")


@pytest.fixture(name="kafka_container", scope="session")
def kafka_container_fixture() -> Generator[KafkaContainerFixture, None, None]:
    """Fixture for getting a running Kafka test container."""
    with KafkaContainerFixture() as kafka_container:
        yield kafka_container


@pytest.fixture(name="mongodb_container", scope="session")
def mongodb_container_fixture() -> Generator[MongoDbContainer, None, None]:
    """Fixture for getting a running MongoDB test container."""
    with MongoDbContainer(image="mongo:6.0.3") as mongodb_container:
        yield mongodb_container


@pytest_asyncio.fixture(name="kafka")
async def empty_kafka_fixture(
    kafka_container: KafkaContainerFixture,
) -> AsyncGenerator[KafkaFixture, None]:
    """Pytest fixture for tests depending on the Kafka-base providers.

    This function-scoped fixture also clears all the Kafka topics.
    """
    config = kafka_container.kafka_config
    async with KafkaEventPublisher.construct(config=config) as publisher:
        kafka_fixture = KafkaFixture(
            config=config,
            kafka_servers=config.kafka_servers,
            cmd_exec_func=kafka_container.wrapped_exec_run,
            publisher=publisher,
        )
        await kafka_fixture.clear_topics()
        yield kafka_fixture


@pytest.fixture(name="mongodb")
def empty_mongodb_fixture(
    mongodb_container: MongoDbContainer,
) -> Generator[MongoDbFixture, None, None]:
    """Pytest fixture for tests depending on the MongoDbDaoFactory DAO.

    This function-scoped fixture also empties all the MongoDB collections.
    """
    config = config_from_mongodb_container(mongodb_container)
    dao_factory = MongoDbDaoFactory(config=config)
    client = mongodb_container.get_connection_client()
    mongodb_fixture = MongoDbFixture(
        client=client,
        config=config,
        dao_factory=dao_factory,
    )
    mongodb_fixture.empty_collections()
    yield mongodb_fixture

    client.close()
