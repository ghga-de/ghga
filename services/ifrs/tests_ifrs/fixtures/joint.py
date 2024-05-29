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
    "OUTBOX_BUCKET",
    "PERMANENT_BUCKET",
    "STAGING_BUCKET",
]

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
    endpoint_aliases: EndpointAliases


@pytest_asyncio.fixture(scope="function")
async def joint_fixture(
    mongodb: MongoDbFixture,
    s3: S3Fixture,
    kafka: KafkaFixture,
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    # merge configs from different sources with the default one:

    node_config = S3ObjectStorageNodeConfig(
        bucket=PERMANENT_BUCKET, credentials=s3.config
    )

    endpoint_aliases = EndpointAliases()

    object_storage_config = S3ObjectStoragesConfig(
        object_storages={
            endpoint_aliases.node1: node_config,
        }
    )
    config = get_config(sources=[mongodb.config, object_storage_config, kafka.config])
    dao_factory = MongoDbDaoFactory(config=config)
    file_metadata_dao = await FileMetadataDaoConstructor.construct(
        dao_factory=dao_factory
    )

    # Prepare the file registry (core)
    async with prepare_core(config=config) as file_registry:
        yield JointFixture(
            config=config,
            mongodb=mongodb,
            s3=s3,
            file_metadata_dao=file_metadata_dao,
            file_registry=file_registry,
            kafka=kafka,
            outbox_bucket=OUTBOX_BUCKET,
            staging_bucket=STAGING_BUCKET,
            endpoint_aliases=endpoint_aliases,
        )
