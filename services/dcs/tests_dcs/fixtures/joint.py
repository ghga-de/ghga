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
    "JointFixture",
    "PopulatedFixture",
    "cleanup_fixture",
    "generate_work_order_token",
    "joint_fixture",
    "populated_fixture",
]

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import timedelta
from uuid import UUID

import httpx
import pytest_asyncio
from ghga_event_schemas import pydantic_ as event_schemas
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils import utc_dates
from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorageNodeConfig,
    S3ObjectStoragesConfig,
)
from hexkit.providers.akafka import KafkaEventSubscriber
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.s3.testutils import S3Fixture, temp_file_object
from hexkit.utils import now_utc_ms_prec
from jwcrypto.jwk import JWK
from pydantic_settings import BaseSettings

from dcs.adapters.outbound.dao import get_drs_dao
from dcs.config import Config, WorkOrderTokenConfig
from dcs.core import models
from dcs.inject import (
    prepare_core,
    prepare_event_subscriber,
    prepare_rest_app,
)
from dcs.ports.inbound.data_repository import DataRepositoryPort
from dcs.ports.outbound.dao import DrsObjectDaoPort
from tests_dcs.fixtures.config import get_config
from tests_dcs.fixtures.utils import (
    generate_token_signing_keys,
    generate_work_order_token,
)

STORAGE_ALIAS = "test"

EXAMPLE_OBJECT_ID = UUID("309b034b-9517-4adc-9e06-c77b09cecfea")
CACHED_OBJECT_ID = UUID("038dfa61-19f6-4279-a894-4e8794013c44")
EXPIRED_OBJECT_ID = UUID("9c8f2155-1fbe-418e-8159-274a4dfc6d8a")

EXAMPLE_FILE = models.AccessTimeDrsObject(
    file_id="examplefile001",
    object_id=EXAMPLE_OBJECT_ID,
    decrypted_sha256="0677de3685577a06862f226bb1bfa8f889e96e59439d915543929fb4f011d096",
    creation_date=now_utc_ms_prec(),
    decrypted_size=12345,
    decryption_secret_id="some-secret",
    encrypted_size=23456,
    s3_endpoint_alias=STORAGE_ALIAS,
    last_accessed=now_utc_ms_prec(),
)


@dataclass
class EndpointAliases:
    valid_node: str = STORAGE_ALIAS
    fake_node: str = f"{STORAGE_ALIAS}_fake"


class EKSSBaseInjector(BaseSettings):
    """Dynamically inject ekss url"""

    ekss_base_url: str


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    bucket_id: str
    data_repository: DataRepositoryPort
    rest_client: httpx.AsyncClient
    event_subscriber: KafkaEventSubscriber
    mongodb: MongoDbFixture
    s3: S3Fixture
    kafka: KafkaFixture
    jwk: JWK
    endpoint_aliases: EndpointAliases


@pytest_asyncio.fixture
async def joint_fixture(
    mongodb: MongoDbFixture,
    s3: S3Fixture,
    kafka: KafkaFixture,
) -> AsyncGenerator[JointFixture]:
    """A fixture that embeds all other fixtures for API-level integration testing"""
    jwk = generate_token_signing_keys()
    auth_key = jwk.export(private_key=False)

    # merge configs from different sources with the default one:
    auth_config = WorkOrderTokenConfig(auth_key=auth_key)
    ekss_config = EKSSBaseInjector(ekss_base_url="http://ekss")

    bucket_id = "test-outbox"

    node_config = S3ObjectStorageNodeConfig(bucket=bucket_id, credentials=s3.config)

    endpoint_aliases = EndpointAliases()

    object_storage_config = S3ObjectStoragesConfig(
        object_storages={
            endpoint_aliases.valid_node: node_config,
        }
    )

    config = get_config(
        sources=[
            mongodb.config,
            object_storage_config,
            kafka.config,
            ekss_config,
            auth_config,
        ],
        kafka_enable_dlq=True,
    )

    # create storage entities:
    await s3.populate_buckets(buckets=[bucket_id])

    # prepare everything
    async with (
        prepare_core(config=config) as data_repository,
        prepare_rest_app(config=config, data_repo_override=data_repository) as app,
        prepare_event_subscriber(
            config=config, data_repo_override=data_repository
        ) as event_subscriber,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield JointFixture(
            config=config,
            bucket_id=bucket_id,
            data_repository=data_repository,
            rest_client=rest_client,
            event_subscriber=event_subscriber,
            mongodb=mongodb,
            s3=s3,
            kafka=kafka,
            jwk=jwk,
            endpoint_aliases=endpoint_aliases,
        )


@dataclass(frozen=True)
class PopulatedFixture:
    """Returned by `populated_fixture()`."""

    mongodb_dao: DrsObjectDaoPort
    joint_fixture: JointFixture
    example_file: models.AccessTimeDrsObject = field(
        default_factory=lambda: EXAMPLE_FILE
    )


@pytest_asyncio.fixture
async def populated_fixture(
    joint_fixture: JointFixture,
) -> AsyncGenerator[PopulatedFixture]:
    """Prepopulate state for an existing DRS object"""
    # publish an event to register a new file for download:
    file_to_register_event = event_schemas.FileInternallyRegistered(
        s3_endpoint_alias=joint_fixture.endpoint_aliases.valid_node,
        file_id=EXAMPLE_FILE.file_id,
        object_id=EXAMPLE_FILE.object_id,
        bucket_id=joint_fixture.bucket_id,
        upload_date=EXAMPLE_FILE.creation_date,
        decrypted_size=EXAMPLE_FILE.decrypted_size,
        decrypted_sha256=EXAMPLE_FILE.decrypted_sha256,
        encrypted_size=1234567,
        encrypted_part_size=1,
        encrypted_parts_md5=["some", "checksum"],
        encrypted_parts_sha256=["some", "checksum"],
        content_offset=1234,
        decryption_secret_id="some-secret",
    )

    await joint_fixture.kafka.publish_event(
        payload=json.loads(file_to_register_event.model_dump_json()),
        type_=joint_fixture.config.file_internally_registered_type,
        topic=joint_fixture.config.file_internally_registered_topic,
    )

    # consume the event:
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_registered_for_download_topic
    ) as recorder:
        await joint_fixture.event_subscriber.run(forever=False)

    # check that an event informing about the newly registered file was published:
    assert len(recorder.recorded_events) == 1
    assert (
        recorder.recorded_events[0].type_
        == joint_fixture.config.file_registered_for_download_type
    )

    file_registered_event = event_schemas.FileRegisteredForDownload(
        **recorder.recorded_events[0].payload
    )
    assert file_registered_event.file_id == EXAMPLE_FILE.file_id
    assert file_registered_event.decrypted_sha256 == EXAMPLE_FILE.decrypted_sha256
    assert file_registered_event.upload_date == EXAMPLE_FILE.creation_date

    dao = await get_drs_dao(dao_factory=joint_fixture.mongodb.dao_factory)

    yield PopulatedFixture(
        mongodb_dao=dao,
        joint_fixture=joint_fixture,
    )


@dataclass
class CleanupFixture:
    """Fixture for cleanup test with DAO and test files"""

    mongodb_dao: DrsObjectDaoPort
    joint: JointFixture
    cached_file_id: str
    expired_file_id: str


@pytest_asyncio.fixture
async def cleanup_fixture(
    joint_fixture: JointFixture,
) -> AsyncGenerator[CleanupFixture]:
    """Set up state for and populate CleanupFixture"""
    # create common db dao to insert test data
    mongodb_dao = await joint_fixture.mongodb.dao_factory.get_dao(
        name="drs_objects",
        dto_model=models.AccessTimeDrsObject,
        id_field="file_id",
    )

    s3 = joint_fixture.s3
    file = EXAMPLE_FILE

    # create AccessTimeDrsObjects for valid cached and expired cached file
    cached_file_id = file.file_id + "_cached"

    test_file_cached = file.model_copy(deep=True)
    test_file_cached.file_id = cached_file_id
    test_file_cached.object_id = CACHED_OBJECT_ID
    test_file_cached.last_accessed = utc_dates.now_as_utc()

    expired_file_id = file.file_id + "_expired"

    test_file_expired = file.model_copy(deep=True)
    test_file_expired.file_id = expired_file_id
    test_file_expired.object_id = EXPIRED_OBJECT_ID
    test_file_expired.last_accessed = utc_dates.now_as_utc() - timedelta(
        days=joint_fixture.config.outbox_cache_timeout
    )

    # populate DB entries
    await mongodb_dao.insert(test_file_cached)
    await mongodb_dao.insert(test_file_expired)

    # populate storage
    with temp_file_object(
        bucket_id=joint_fixture.bucket_id,
        object_id=str(test_file_cached.object_id),
    ) as cached_file:
        with temp_file_object(
            bucket_id=joint_fixture.bucket_id,
            object_id=str(test_file_expired.object_id),
        ) as expired_file:
            await s3.populate_file_objects([cached_file, expired_file])

    yield CleanupFixture(
        mongodb_dao=mongodb_dao,
        joint=joint_fixture,
        cached_file_id=cached_file_id,
        expired_file_id=expired_file_id,
    )
