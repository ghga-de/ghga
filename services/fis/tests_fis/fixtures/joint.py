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
from fis.config import Config
from fis.core.models import UploadMetadataBase
from fis.inject import prepare_core, prepare_rest_app
from fis.ports.inbound.ingest import (
    LegacyUploadMetadataProcessorPort,
    UploadMetadataProcessorPort,
)
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.crypt import (
    KeyPair,
    encode_key,
    generate_key_pair,
)
from ghga_service_commons.utils.simple_token import generate_token_and_hash
from hexkit.providers.akafka.testutils import KafkaFixture

from tests_fis.fixtures.config import get_config

TEST_PAYLOAD = UploadMetadataBase(
    file_id="abc",
    object_id="happy_little_object",
    part_size=16 * 1024**2,
    unencrypted_size=50 * 1024**2,
    encrypted_size=50 * 1024**2 + 128,
    unencrypted_checksum="def",
    encrypted_md5_checksums=["a", "b", "c"],
    encrypted_sha256_checksums=["a", "b", "c"],
)


@dataclass
class JointFixture:
    """Holds generated test keypair and configured container"""

    config: Config
    keypair: KeyPair
    token: str
    payload: UploadMetadataBase
    kafka: KafkaFixture
    rest_client: httpx.AsyncClient
    s3_endpoint_alias: str
    upload_metadata_processor: UploadMetadataProcessorPort
    legacy_upload_metadata_processor: LegacyUploadMetadataProcessorPort


@pytest_asyncio.fixture
async def joint_fixture(kafka: KafkaFixture) -> AsyncGenerator[JointFixture, None]:
    """Generate keypair for testing and setup container with updated config"""
    keypair = generate_key_pair()
    private_key = encode_key(key=keypair.private)

    token, token_hash = generate_token_and_hash()

    config = get_config(sources=[kafka.config])
    # cannot update inplace, copy and update instead
    config = config.model_copy(
        update={"private_key": private_key, "token_hashes": [token_hash]}
    )
    async with prepare_core(config=config) as (
        upload_metadata_processor,
        legacy_upload_metadata_processor,
    ):
        async with prepare_rest_app(
            config=config,
            core_override=(upload_metadata_processor, legacy_upload_metadata_processor),
        ) as app:
            async with AsyncTestClient(app=app) as rest_client:
                yield JointFixture(
                    config=config,
                    keypair=keypair,
                    payload=TEST_PAYLOAD,
                    token=token,
                    kafka=kafka,
                    rest_client=rest_client,
                    s3_endpoint_alias=config.selected_storage_alias,
                    upload_metadata_processor=upload_metadata_processor,
                    legacy_upload_metadata_processor=legacy_upload_metadata_processor,
                )
