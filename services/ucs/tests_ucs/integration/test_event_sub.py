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

"""Integration tests for the event subscriber"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from ghga_event_schemas.pydantic_ import FileDeletionRequested, FileInternallyRegistered
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.utils import now_utc_ms_prec

from tests_ucs.fixtures import utils
from tests_ucs.fixtures.config import get_config
from ucs.inject import prepare_event_subscriber
from ucs.ports.inbound.controller import UploadControllerPort


@pytest.mark.asyncio
async def test_file_internally_registered(kafka: KafkaFixture):
    """Test that consuming a FileInternallyRegistered event triggers the right method
    on the UploadController class.
    """
    core_mock = AsyncMock(spec=UploadControllerPort)
    config = get_config(sources=[kafka.config])
    async with prepare_event_subscriber(
        config=config, core_override=core_mock
    ) as event_subscriber:
        event = FileInternallyRegistered(
            file_id=uuid4(),
            archive_date=now_utc_ms_prec(),
            storage_alias="test",
            bucket_id="permanent-bucket",
            secret_id="my-secret",
            decrypted_size=utils.DECRYPTED_SIZE,
            encrypted_size=utils.ENCRYPTED_SIZE,
            decrypted_sha256="abc123",
            encrypted_parts_md5=["a1", "b2"],
            encrypted_parts_sha256=["a1", "b2"],
            part_size=utils.PART_SIZE,
        )

        await kafka.publish_event(
            payload=event.model_dump(mode="json"),
            type_=config.file_internally_registered_type,
            topic=config.file_internally_registered_topic,
        )
        await event_subscriber.run(forever=False)
    core_mock.process_internal_file_registration.assert_awaited_once()


@pytest.mark.asyncio
async def test_file_deletion_requested(kafka: KafkaFixture):
    """Test that consuming a FileDeletionRequested event triggers the right method
    on the UploadController class.
    """
    core_mock = AsyncMock(spec=UploadControllerPort)
    config = get_config(sources=[kafka.config])
    async with prepare_event_subscriber(
        config=config, core_override=core_mock
    ) as event_subscriber:
        event = FileDeletionRequested(file_id=uuid4())

        await kafka.publish_event(
            payload=event.model_dump(mode="json"),
            type_=config.file_deletion_request_type,
            topic=config.file_deletion_request_topic,
        )
        await event_subscriber.run(forever=False)
    core_mock.process_file_deletion_requested.assert_awaited_once()
