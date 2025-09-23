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

"""Testing for DLQ functionality"""

from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from hexkit.providers.akafka.provider.eventsub import HeaderNames
from hexkit.providers.akafka.testutils import KafkaFixture

from tests.fixtures.config import get_config
from uos.inject import prepare_event_subscriber

pytestmark = pytest.mark.asyncio()
UPSERTED = "upserted"

TEST_FILE_UPLOAD_BOX_ID = UUID("f139ab68-56cc-4ca1-8866-2ffc8f297728")
TEST_PAYLOAD: dict[str, Any] = {
    "id": str(TEST_FILE_UPLOAD_BOX_ID),
    "locked": False,
    "file_count": 0,
    "size": 0,
    "storage_alias": "test-alias",
}


async def test_use_dlq_on_failure(kafka: KafkaFixture):
    """Test that the DLQ is enabled.

    This test should ensure that if the event sub fails to process an event,
    it publishes the event to the dead-letter queue (DLQ).
    We only have to test either upsert or delete, because the framework handles both
    cases the same way.
    """
    config = get_config(sources=[kafka.config], kafka_enable_dlq=True)

    # Publish an event that will cause a failure
    await kafka.publish_event(
        topic=config.file_upload_box_topic,
        type_=UPSERTED,
        key=str(TEST_FILE_UPLOAD_BOX_ID),
        payload={"some-field": "some-value"},
    )

    async with (
        prepare_event_subscriber(
            config=config, upload_orchestrator_override=AsyncMock()
        ) as event_subscriber,
        kafka.record_events(in_topic=config.kafka_dlq_topic) as dlq_recorder,
    ):
        await event_subscriber.run(forever=False)

    # Check that the event was published to the DLQ
    assert len(dlq_recorder.recorded_events) == 1
    event = dlq_recorder.recorded_events[0]
    assert event.key == str(TEST_FILE_UPLOAD_BOX_ID)
    assert event.type_ == UPSERTED
    assert event.payload == {"some-field": "some-value"}


async def test_reconsume_from_retry(kafka: KafkaFixture):
    """Test that we can re-consume from the retry topic.

    This test should ensure that if an event is retried, it can be consumed again
    from the retry topic.
    """
    config = get_config(sources=[kafka.config], kafka_enable_dlq=True)
    assert config.kafka_enable_dlq

    # Publish a valid event, but to the retry topic.
    await kafka.publish_event(
        topic=f"retry-{config.service_name}",
        type_=UPSERTED,
        key=str(TEST_FILE_UPLOAD_BOX_ID),
        payload=TEST_PAYLOAD,
        headers={HeaderNames.ORIGINAL_TOPIC: config.file_upload_box_topic},
    )

    core_mock = AsyncMock()
    async with prepare_event_subscriber(
        config=config, upload_orchestrator_override=core_mock
    ) as event_subscriber:
        await event_subscriber.run(forever=False)

    # Check that the upload orchestrator's upsert_file_upload_box method was called
    assert core_mock.upsert_file_upload_box.call_count == 1
