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
"""Bundle test fixtures together"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import httpx
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.crypt import (
    KeyPair,
    encode_key,
    generate_key_pair,
)
from ghga_service_commons.utils.simple_token import generate_token_and_hash
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture

from fis.config import Config
from fis.core.models import UploadMetadataBase
from fis.inject import get_file_validation_success_dao, prepare_core, prepare_rest_app
from fis.ports.inbound.ingest import (
    LegacyUploadMetadataProcessorPort,
    UploadMetadataProcessorPort,
)
from fis.ports.outbound.daopub import FileUploadValidationSuccessDao
from tests_fis.fixtures.config import get_config

__all__ = ["joint_fixture", "JointFixture", "TEST_PAYLOAD"]

TEST_PAYLOAD = UploadMetadataBase(
    file_id="abc",
    object_id="happy_little_object",
    part_size=16 * 1024**2,
    unencrypted_size=50 * 1024**2,
    encrypted_size=50 * 1024**2 + 128,
    unencrypted_checksum="def",
    encrypted_md5_checksums=["a", "b", "c"],
    encrypted_sha256_checksums=["a", "b", "c"],
    storage_alias="staging",
)


@dataclass
class JointFixture:
    """Holds generated test keypair and configured container"""

    config: Config
    keypair: KeyPair
    token: str
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    rest_client: httpx.AsyncClient
    upload_metadata_processor: UploadMetadataProcessorPort
    legacy_upload_metadata_processor: LegacyUploadMetadataProcessorPort
    dao: FileUploadValidationSuccessDao


@pytest_asyncio.fixture
async def joint_fixture(
    kafka: KafkaFixture, mongodb: MongoDbFixture
) -> AsyncGenerator[JointFixture, None]:
    """Generate keypair for testing and setup container with updated config"""
    keypair = generate_key_pair()
    private_key = encode_key(key=keypair.private)

    token, token_hash = generate_token_and_hash()

    config = get_config(sources=[kafka.config, mongodb.config])
    # cannot update inplace, copy and update instead
    config = config.model_copy(
        update={"private_key": private_key, "token_hashes": [token_hash]}
    )
    async with (
        prepare_core(config=config) as (
            upload_metadata_processor,
            legacy_upload_metadata_processor,
        ),
        prepare_rest_app(
            config=config,
            core_override=(upload_metadata_processor, legacy_upload_metadata_processor),
        ) as app,
        get_file_validation_success_dao(config=config) as dao,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield JointFixture(
            config=config,
            keypair=keypair,
            token=token,
            kafka=kafka,
            mongodb=mongodb,
            rest_client=rest_client,
            upload_metadata_processor=upload_metadata_processor,
            legacy_upload_metadata_processor=legacy_upload_metadata_processor,
            dao=dao,
        )
