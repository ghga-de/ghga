# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
    "OUTBOX_BUCKET",
    "PERMANENT_BUCKET",
    "STAGING_BUCKET",
    "JointFixture",
]

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorageNodeConfig,
    S3ObjectStoragesConfig,
)
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb import MongoDbDaoFactory
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.s3.testutils import S3Fixture

from ifrs.adapters.outbound.dao import get_file_metadata_dao
from ifrs.config import Config
from ifrs.inject import prepare_core, prepare_event_subscriber
from ifrs.ports.inbound.file_registry import FileRegistryPort
from ifrs.ports.outbound.dao import FileMetadataDaoPort
from tests_ifrs.fixtures.config import get_config

OUTBOX_BUCKET = "outbox"
PERMANENT_BUCKET = "permanent"
STAGING_BUCKET = "staging"

STORAGE_ALIASES = ("test", "test2")


@dataclass
class StorageAliases:
    node1: str = STORAGE_ALIASES[0]
    node2: str = STORAGE_ALIASES[1]
    fake: str = f"{STORAGE_ALIASES[0]}_fake"


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    mongodb: MongoDbFixture
    s3: S3Fixture
    file_metadata_dao: FileMetadataDaoPort
    file_registry: FileRegistryPort
    kafka: KafkaFixture
    outbox_bucket: str
    staging_bucket: str
    storage_aliases: StorageAliases
    event_subscriber: KafkaEventSubscriber


@pytest_asyncio.fixture(scope="function")
async def joint_fixture(
    mongodb: MongoDbFixture,
    s3: S3Fixture,
    kafka: KafkaFixture,
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    node_config = S3ObjectStorageNodeConfig(
        bucket=PERMANENT_BUCKET, credentials=s3.config
    )

    storage_aliases = StorageAliases()

    object_storage_config = S3ObjectStoragesConfig(
        object_storages={
            storage_aliases.node1: node_config,
        }
    )

    # merge configs from different sources with the default one:
    config = get_config(sources=[mongodb.config, object_storage_config, kafka.config])
    dao_factory = MongoDbDaoFactory(config=config)
    file_metadata_dao = await get_file_metadata_dao(dao_factory=dao_factory)

    # Prepare the file registry (core)
    async with prepare_core(config=config) as file_registry:
        async with prepare_event_subscriber(
            config=config,
            core_override=file_registry,
        ) as event_subscriber:
            yield JointFixture(
                config=config,
                mongodb=mongodb,
                s3=s3,
                file_metadata_dao=file_metadata_dao,
                file_registry=file_registry,
                kafka=kafka,
                event_subscriber=event_subscriber,
                outbox_bucket=OUTBOX_BUCKET,
                staging_bucket=STAGING_BUCKET,
                storage_aliases=storage_aliases,
            )
