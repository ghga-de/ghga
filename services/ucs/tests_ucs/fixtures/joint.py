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

"""Join the functionality of all fixtures for API-level integration testing."""

__all__ = ["JointFixture", "joint_fixture"]

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import httpx
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorageNodeConfig,
    S3ObjectStoragesConfig,
)
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.s3.testutils import S3Fixture

from tests_ucs.fixtures.config import get_config
from tests_ucs.fixtures.example_data import STORAGE_ALIASES
from ucs.adapters.outbound.dao import DaoCollectionTranslator
from ucs.config import Config
from ucs.inject import (
    get_file_upload_received_dao,
    prepare_core,
    prepare_event_subscriber,
    prepare_rest_app,
    prepare_storage_inspector,
)
from ucs.ports.inbound.file_service import FileMetadataServicePort
from ucs.ports.inbound.storage_inspector import StorageInspectorPort
from ucs.ports.inbound.upload_service import UploadServicePort
from ucs.ports.outbound.dao import DaoCollectionPort
from ucs.ports.outbound.daopub import FileUploadReceivedDao


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    daos: DaoCollectionPort
    upload_service: UploadServicePort
    file_metadata_service: FileMetadataServicePort
    rest_client: httpx.AsyncClient
    event_subscriber: KafkaEventSubscriber
    file_upload_received_dao: FileUploadReceivedDao
    mongodb: MongoDbFixture
    kafka: KafkaFixture
    s3: S3Fixture
    bucket_id: str
    inbox_inspector: StorageInspectorPort


@pytest_asyncio.fixture(scope="function")
async def joint_fixture(
    mongodb: MongoDbFixture,
    kafka: KafkaFixture,
    s3: S3Fixture,
) -> AsyncGenerator[JointFixture, None]:
    """A fixture that embeds all other fixtures for API-level integration testing."""
    bucket_id = "test-inbox"

    node_config = S3ObjectStorageNodeConfig(bucket=bucket_id, credentials=s3.config)
    object_storages_config = S3ObjectStoragesConfig(
        object_storages={
            STORAGE_ALIASES[0]: node_config,
        }
    )

    # merge configs from different sources with the default one:
    config = get_config(
        sources=[mongodb.config, kafka.config, object_storages_config],
        kafka_enable_dlq=True,
    )

    daos = await DaoCollectionTranslator.construct(provider=mongodb.dao_factory)
    await s3.populate_buckets([bucket_id])

    # Assemble joint fixture with config injection
    async with (
        prepare_core(config=config) as (
            upload_service,
            file_metadata_service,
        ),
        prepare_storage_inspector(config=config) as inbox_inspector,
        prepare_rest_app(
            config=config, core_override=(upload_service, file_metadata_service)
        ) as app,
        prepare_event_subscriber(
            config=config, core_override=(upload_service, file_metadata_service)
        ) as event_subscriber,
        get_file_upload_received_dao(config=config) as file_upload_received_dao,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield JointFixture(
            config=config,
            daos=daos,
            upload_service=upload_service,
            file_metadata_service=file_metadata_service,
            rest_client=rest_client,
            event_subscriber=event_subscriber,
            file_upload_received_dao=file_upload_received_dao,
            mongodb=mongodb,
            kafka=kafka,
            s3=s3,
            bucket_id=bucket_id,
            inbox_inspector=inbox_inspector,
        )
