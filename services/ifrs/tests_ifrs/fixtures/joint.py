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

"""Join the functionality of all fixtures for API-level integration testing."""

__all__ = [
    "JointFixture",
    "get_joint_fixture",
]

import socket
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorageNodeConfig,
    S3ObjectStoragesConfig,
)
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.s3.testutils import S3Fixture
from ifrs.adapters.outbound.dao import FileMetadataDaoConstructor
from ifrs.config import Config
from ifrs.inject import prepare_core
from ifrs.ports.inbound.file_registry import FileRegistryPort
from ifrs.ports.outbound.dao import FileMetadataDaoPort
from pytest_asyncio.plugin import _ScopeName

from tests_ifrs.fixtures.config import get_config

OUTBOX_BUCKET = "outbox"
PERMANENT_BUCKET = "permanent"
STAGING_BUCKET = "staging"

STORAGE_ALIASES = ("test", "test2")


@dataclass
class EndpointAliases:
    node1: str = STORAGE_ALIASES[0]
    node2: str = STORAGE_ALIASES[1]
    fake: str = f"{STORAGE_ALIASES[0]}_fake"


def get_free_port() -> int:
    """Finds and returns a free port on localhost."""
    sock = socket.socket()
    sock.bind(("", 0))
    return int(sock.getsockname()[1])


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    mongodb: MongoDbFixture
    s3: S3Fixture
    second_s3: S3Fixture
    file_metadata_dao: FileMetadataDaoPort
    file_registry: FileRegistryPort
    kafka: KafkaFixture
    outbox_bucket: str
    staging_bucket: str
    endpoint_aliases: EndpointAliases

    async def reset_state(self):
        """Completely reset fixture states"""
        await self.s3.empty_buckets()
        await self.second_s3.empty_buckets()
        self.mongodb.empty_collections()
        self.kafka.clear_topics()


async def joint_fixture_function(
    mongodb_fixture: MongoDbFixture,
    s3_fixture: S3Fixture,
    second_s3_fixture: S3Fixture,
    kafka_fixture: KafkaFixture,
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    # merge configs from different sources with the default one:

    node_config = S3ObjectStorageNodeConfig(
        bucket=PERMANENT_BUCKET, credentials=s3_fixture.config
    )
    second_node_config = S3ObjectStorageNodeConfig(
        bucket=PERMANENT_BUCKET, credentials=second_s3_fixture.config
    )

    endpoint_aliases = EndpointAliases()

    object_storage_config = S3ObjectStoragesConfig(
        object_storages={
            endpoint_aliases.node1: node_config,
            endpoint_aliases.node2: second_node_config,
        }
    )
    config = get_config(
        sources=[mongodb_fixture.config, object_storage_config, kafka_fixture.config]
    )
    dao_factory = MongoDbDaoFactory(config=config)
    file_metadata_dao = await FileMetadataDaoConstructor.construct(
        dao_factory=dao_factory
    )

    # create a DI container instance:translators
    async with prepare_core(config=config) as file_registry:
        # create storage entities:
        await s3_fixture.populate_buckets(
            buckets=[
                OUTBOX_BUCKET,
                STAGING_BUCKET,
                PERMANENT_BUCKET,
            ]
        )
        await second_s3_fixture.populate_buckets(
            buckets=[
                OUTBOX_BUCKET,
                STAGING_BUCKET,
                PERMANENT_BUCKET,
            ]
        )

        yield JointFixture(
            config=config,
            mongodb=mongodb_fixture,
            s3=s3_fixture,
            second_s3=second_s3_fixture,
            file_metadata_dao=file_metadata_dao,
            file_registry=file_registry,
            kafka=kafka_fixture,
            outbox_bucket=OUTBOX_BUCKET,
            staging_bucket=STAGING_BUCKET,
            endpoint_aliases=endpoint_aliases,
        )


def get_joint_fixture(scope: _ScopeName = "function"):
    """Produce a joint fixture with desired scope"""
    return pytest_asyncio.fixture(joint_fixture_function, scope=scope)
