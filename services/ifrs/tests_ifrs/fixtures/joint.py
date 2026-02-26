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
    "DOWNLOAD_BUCKET",
    "INTERROGATION_BUCKET",
    "PERMANENT_BUCKET",
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
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.s3.testutils import FederatedS3Fixture

from ifrs.adapters.outbound.dao import get_file_dao
from ifrs.config import Config
from ifrs.inject import prepare_core, prepare_event_subscriber
from ifrs.ports.inbound.file_registry import FileRegistryPort
from ifrs.ports.outbound.dao import FileMetadataDao
from tests_ifrs.fixtures.config import get_config
from tests_ifrs.fixtures.utils import (
    DOWNLOAD_BUCKET,
    INTERROGATION_BUCKET,
    PERMANENT_BUCKET,
    STORAGE_ALIASES,
)


@dataclass
class StorageAliases:
    node0: str = STORAGE_ALIASES[0]
    node1: str = STORAGE_ALIASES[1]
    node2: str = STORAGE_ALIASES[2]
    fake_node: str = "notreal"


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    mongodb: MongoDbFixture
    federated_s3: FederatedS3Fixture
    file_metadata_dao: FileMetadataDao
    file_registry: FileRegistryPort
    kafka: KafkaFixture
    storage_aliases: StorageAliases
    event_subscriber: KafkaEventSubscriber


@pytest_asyncio.fixture(scope="function")
async def joint_fixture(
    mongodb: MongoDbFixture, federated_s3: FederatedS3Fixture, kafka: KafkaFixture
) -> AsyncGenerator[JointFixture]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    object_storages: dict[str, S3ObjectStorageNodeConfig] = {}
    s3_credential_configs = federated_s3.get_configs_by_alias()
    for storage_alias in STORAGE_ALIASES:
        # Populate the three main buckets for each data hub (storage alias)
        await federated_s3.storages[storage_alias].populate_buckets(
            buckets=[INTERROGATION_BUCKET, PERMANENT_BUCKET, DOWNLOAD_BUCKET]
        )
        # Create storage config with the permanent bucket as the bucket ID because
        #  the permanent bucket is the one bucket that IFRS has ownership over
        object_storages[storage_alias] = S3ObjectStorageNodeConfig(
            bucket=PERMANENT_BUCKET, credentials=s3_credential_configs[storage_alias]
        )

    storage_aliases = StorageAliases()

    object_storage_config = S3ObjectStoragesConfig(object_storages=object_storages)

    # merge configs from different sources with the default one:
    config = get_config(sources=[mongodb.config, object_storage_config, kafka.config])
    file_metadata_dao = await get_file_dao(dao_factory=mongodb.dao_factory)

    # Prepare the file registry (core)
    async with (
        prepare_core(config=config) as file_registry,
        prepare_event_subscriber(
            config=config,
            core_override=file_registry,
        ) as event_subscriber,
    ):
        yield JointFixture(
            config=config,
            mongodb=mongodb,
            federated_s3=federated_s3,
            file_metadata_dao=file_metadata_dao,
            file_registry=file_registry,
            kafka=kafka,
            event_subscriber=event_subscriber,
            storage_aliases=storage_aliases,
        )
