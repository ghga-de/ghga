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

"""Integration tests for the event sub functionality."""

from unittest.mock import AsyncMock

import pytest
from hexkit.custom_types import JsonObject
from hexkit.providers.akafka.provider.eventsub import HeaderNames
from hexkit.providers.akafka.testutils import KafkaFixture

from rts.inject import prepare_event_subscriber
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()

ARTIFACT_NAME = "added_accessions"
TEST_ACCESSION = "test_accession"
TEST_KEY = f"{ARTIFACT_NAME}:{TEST_ACCESSION}"
UPSERTED = "upserted"
DELETED = "deleted"
CONTENT = {"samples": [{"accession": "sample1"}]}
TEST_PAYLOAD: JsonObject = {
    "artifact_name": ARTIFACT_NAME,
    "content": CONTENT,
    "study_accession": TEST_ACCESSION,
}


async def test_event_sub_upsert(kafka: KafkaFixture):
    """Test the event sub upsert functionality.

    This test should ensure that the upsert event triggers the appropriate core method.
    It does not test what happens in the core, only that it is called correctly.
    """
    config = get_config(sources=[kafka.config])

    # Publish the upsert event
    await kafka.publish_event(
        topic=config.artifact_topic,
        type_=UPSERTED,
        key=TEST_KEY,
        payload=TEST_PAYLOAD,
    )

    reverse_transpiler = AsyncMock()
    async with prepare_event_subscriber(
        config=config, reverse_transpiler_override=reverse_transpiler
    ) as event_subscriber:
        await event_subscriber.run(forever=False)

    assert reverse_transpiler.upsert_metadata.call_count == 1


async def test_event_sub_delete(kafka: KafkaFixture):
    """Test the event sub delete functionality.

    This test should ensure that the delete event triggers the appropriate core method.
    It does not test what happens in the core, only that it is called correctly.
    """
    config = get_config(sources=[kafka.config])

    # Publish the delete event
    await kafka.publish_event(
        topic=config.artifact_topic,
        type_=DELETED,
        key=TEST_KEY,
        payload={},
    )

    reverse_transpiler = AsyncMock()
    async with prepare_event_subscriber(
        config=config, reverse_transpiler_override=reverse_transpiler
    ) as event_subscriber:
        await event_subscriber.run(forever=False)

    assert reverse_transpiler.delete_metadata.call_count == 1


async def test_ignore_non_added_accessions(kafka: KafkaFixture):
    """Test that the event sub ignores non-add_accessions Artifact events.

    This test should ensure that the event sub does not trigger any core methods
    for events that are not added_accessions.
    """
    config = get_config(sources=[kafka.config])

    # Publish the upsert event
    await kafka.publish_event(
        topic=config.artifact_topic,
        type_=UPSERTED,
        key=f"some_other_artifact:{TEST_ACCESSION}",
        payload={
            "artifact_name": "some_other_artifact",
            "content": CONTENT,
            "study_accession": TEST_ACCESSION,
        },
    )

    reverse_transpiler = AsyncMock()
    async with prepare_event_subscriber(
        config=config, reverse_transpiler_override=reverse_transpiler
    ) as event_subscriber:
        await event_subscriber.run(forever=False)
        assert reverse_transpiler.upsert_metadata.call_count == 0

        # Test with a delete event
        await kafka.publish_event(
            topic=config.artifact_topic,
            type_=DELETED,
            key=f"some_other_artifact:{TEST_ACCESSION}",
            payload={},
        )
        await event_subscriber.run(forever=False)
        assert reverse_transpiler.delete_metadata.call_count == 0


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
        topic=config.artifact_topic,
        type_=UPSERTED,
        key=TEST_KEY,
        payload={
            "artifact_name": ARTIFACT_NAME,
            "corntent": CONTENT,  # Note the typo to simulate failure
            "study_accession": TEST_ACCESSION,
        },
    )

    async with (
        prepare_event_subscriber(
            config=config, reverse_transpiler_override=AsyncMock()
        ) as event_subscriber,
        kafka.record_events(in_topic=config.kafka_dlq_topic) as dlq_recorder,
    ):
        await event_subscriber.run(forever=False)

    # Check that the event was published to the DLQ
    assert len(dlq_recorder.recorded_events) == 1
    event = dlq_recorder.recorded_events[0]
    assert event.key == TEST_KEY
    assert event.type_ == UPSERTED
    assert event.payload == {
        "artifact_name": ARTIFACT_NAME,
        "corntent": CONTENT,
        "study_accession": TEST_ACCESSION,
    }


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
        key=TEST_KEY,
        payload=TEST_PAYLOAD,
        headers={HeaderNames.ORIGINAL_TOPIC: config.artifact_topic},
    )

    reverse_transpiler = AsyncMock()
    async with prepare_event_subscriber(
        config=config, reverse_transpiler_override=reverse_transpiler
    ) as event_subscriber:
        await event_subscriber.run(forever=False)

    # Check that the reverse_transpiler was called with the upsert_metadata method
    assert reverse_transpiler.upsert_metadata.call_count == 1
