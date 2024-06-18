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
"""Tests for the outbox (mongokafka) dao publisher."""

import pytest
from ghga_event_schemas.pydantic_ import FileUploadValidationSuccess
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.correlation import new_correlation_id, set_correlation_id
from hexkit.providers.akafka.testutils import ExpectedEvent

from fis.inject import get_file_validation_success_dao
from tests_fis.fixtures.joint import TEST_PAYLOAD, JointFixture


@pytest.mark.asyncio()
async def test_dto_to_event(joint_fixture: JointFixture):
    """Make sure the dto_to_event piece of the mongokafka dao is set up right.

    The expected event is a FileUploadValidationSuccess event.
    """
    config = joint_fixture.config
    async with get_file_validation_success_dao(config=config) as outbox_dao:
        dto = FileUploadValidationSuccess(
            upload_date=now_as_utc().isoformat(),
            file_id=TEST_PAYLOAD.file_id,
            object_id=TEST_PAYLOAD.object_id,
            bucket_id=joint_fixture.config.source_bucket_id,
            s3_endpoint_alias=joint_fixture.s3_endpoint_alias,
            decrypted_size=TEST_PAYLOAD.unencrypted_size,
            decryption_secret_id="",
            content_offset=0,
            encrypted_part_size=TEST_PAYLOAD.part_size,
            encrypted_parts_md5=TEST_PAYLOAD.encrypted_md5_checksums,
            encrypted_parts_sha256=TEST_PAYLOAD.encrypted_sha256_checksums,
            decrypted_sha256=TEST_PAYLOAD.unencrypted_checksum,
        )

        expected_event = ExpectedEvent(
            payload=dto.model_dump(), type_="upserted", key=dto.file_id
        )

        async with (
            set_correlation_id(new_correlation_id()),
            joint_fixture.kafka.expect_events(
                events=[expected_event],
                in_topic=config.file_upload_validation_success_topic,
            ),
        ):
            await outbox_dao.upsert(dto)
