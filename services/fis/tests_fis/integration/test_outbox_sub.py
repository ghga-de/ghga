# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Integration tests for the outbox subscriber"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from fis.core import models
from fis.inject import prepare_event_subscriber
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.utils import now_utc_ms_prec
from tests_fis.fixtures.config import get_config
from tests_fis.fixtures.utils import create_file_under_interrogation

pytestmark = pytest.mark.asyncio()


async def test_changed(kafka: KafkaFixture):
    """Test the `.changed()` method of the outbox subscriber for when we receive
    FileUpload upsertions.
    """
    # Get config and splice in the kafka fixture's connection information
    config = get_config(sources=[kafka.config])

    # Create a FileUnderInterrogation and publish it to the file uploads topic
    file = create_file_under_interrogation("HUB1")
    file.state = "inbox"
    await kafka.publish_event(
        payload=file.model_dump(),
        type_="upserted",
        topic=config.file_upload_topic,
        key=str(file.id),
    )

    # Consume the event
    core_mock = AsyncMock()
    async with prepare_event_subscriber(
        config=config, core_override=core_mock
    ) as outbox_consumer:
        await outbox_consumer.run(forever=False)

    # Verify that the outbox subscriber called the right core method
    core_mock.process_file_upload.assert_awaited_once_with(file=file)


async def test_deleted(kafka: KafkaFixture):
    """Test the `.deleted()` method of the outbox subscriber for when we receive
    FileUpload deletions.
    """
    # Get config and splice in the kafka fixture's connection information
    config = get_config(sources=[kafka.config])

    # Create a FileUnderInterrogation and publish it to the file uploads topic
    file = create_file_under_interrogation("HUB1")
    file.state = "cancelled"
    await kafka.publish_event(
        payload={},
        type_="deleted",
        topic=config.file_upload_topic,
        key=str(file.id),
    )

    # Consume the event
    core_mock = AsyncMock()
    async with prepare_event_subscriber(
        config=config, core_override=core_mock
    ) as outbox_consumer:
        await outbox_consumer.run(forever=False)

    # Verify that the outbox subscriber called the right core method
    core_mock.delete_file.assert_awaited_once_with(file_id=file.id)


async def test_upload_box_priority_changed(kafka: KafkaFixture):
    """Test that an upserted upload box priority list reaches the core with only the
    file upload box IDs, as `box_id`.
    """
    config = get_config(sources=[kafka.config])

    entries = [
        event_schemas.UploadBoxPriorityEntry(
            research_data_upload_box_id=uuid4(), file_upload_box_id=uuid4()
        )
        for _ in range(2)
    ]
    priority = event_schemas.UploadBoxPriority(
        id="global",
        version=7,
        changed_by=uuid4(),
        last_changed=now_utc_ms_prec(),
        entries=entries,
    )
    await kafka.publish_event(
        payload=priority.model_dump(mode="json"),
        type_="upserted",
        topic=config.upload_box_priority_topic,
        key=priority.id,
    )

    core_mock = AsyncMock()
    async with prepare_event_subscriber(
        config=config, core_override=core_mock
    ) as outbox_consumer:
        await outbox_consumer.run(forever=False)

    expected_priority = models.UploadBoxPriority(
        id="global",
        version=7,
        entries=[
            models.UploadBoxPriorityEntry(box_id=entry.file_upload_box_id)
            for entry in entries
        ],
    )
    core_mock.store_upload_box_priority.assert_awaited_once_with(
        priority=expected_priority
    )


async def test_upload_box_priority_deleted(kafka: KafkaFixture):
    """Test that a deleted upload box priority list reaches the core"""
    config = get_config(sources=[kafka.config])

    await kafka.publish_event(
        payload={},
        type_="deleted",
        topic=config.upload_box_priority_topic,
        key="global",
    )

    core_mock = AsyncMock()
    async with prepare_event_subscriber(
        config=config, core_override=core_mock
    ) as outbox_consumer:
        await outbox_consumer.run(forever=False)

    core_mock.clear_upload_box_priority.assert_awaited_once_with(priority_id="global")
