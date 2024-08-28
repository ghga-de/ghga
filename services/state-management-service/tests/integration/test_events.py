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
"""Integration tests for the kafka state management."""

from contextlib import suppress
from typing import Any

import pytest
from aiokafka import AIOKafkaConsumer
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.akafka.testutils import KafkaFixture

from sms.inject import prepare_rest_app
from tests.fixtures.config import get_config
from tests.fixtures.utils import VALID_BEARER_TOKEN

pytestmark = pytest.mark.asyncio()

TEST_TOPIC1 = "topic1"
TEST_TOPIC2 = "topic2"
TEST_TYPE_AND_KEY = {"type_": "test_event", "key": "key1"}

TEST_EVENT1 = {
    "payload": {"test": "event1"},
    "topic": TEST_TOPIC1,
    **TEST_TYPE_AND_KEY,
}
TEST_EVENT2 = {
    "payload": {"test": "event2"},
    "topic": TEST_TOPIC1,
    **TEST_TYPE_AND_KEY,
}
TEST_EVENT3 = {
    "payload": {"test": "event3"},
    "topic": TEST_TOPIC2,
    **TEST_TYPE_AND_KEY,
}
# 2 events in topic1, 1 event in topic2
TEST_EVENTS = [TEST_EVENT1, TEST_EVENT2, TEST_EVENT3]
TEST_TOPICS = [TEST_TOPIC1, TEST_TOPIC2]


@pytest.mark.parametrize(
    "events_to_publish", [TEST_EVENTS, []], ids=["EventsPublished", "NoEventsPublished"]
)
@pytest.mark.parametrize(
    "topics_to_clear",
    [
        [],
        TEST_TOPICS,
        [TEST_TOPIC1],
        [TEST_TOPIC2],
        ["does-not-exist"],
    ],
    ids=[
        "ClearAllTopicsByDefault",
        "ClearAllTopicsExplicitly",
        "ClearTopic1",
        "ClearTopic2",
        "ClearNonExistentTopic",
    ],
)
async def test_clear_topics_happy(
    kafka: KafkaFixture,
    events_to_publish: list[dict[str, Any]],
    topics_to_clear: list[str],
):
    """Test that topics can be cleared."""
    config = get_config(sources=[kafka.config])

    # Publish events if applicable
    published_topics: set[str] = set()
    for event in events_to_publish:
        published_topics.add(event["topic"])
        await kafka.publish_event(**event)

    # Call the endpoint to delete the topics in topics_to_clear
    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.delete(
            "/events/",
            params={"topic": topics_to_clear},
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 204

    # Check that the topics have been cleared
    if published_topics:
        consumer = AIOKafkaConsumer(
            *published_topics,
            bootstrap_servers=kafka.kafka_servers[0],
            group_id="sms",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            consumer_timeout_ms=2000,
        )
        await consumer.start()

        # Get a list of the topics cleared -- an empty topics_to_clear means all topics
        # (ignore internal topics for the test)
        cleared_topics = topics_to_clear if topics_to_clear else published_topics

        # Calculate how many events should have been deleted
        affected_event_count = len(
            [event for event in events_to_publish if event["topic"] in cleared_topics]
        )

        # Calculate how many events should remain
        num_records_remaining = len(events_to_publish) - affected_event_count

        # Verify that the topics have been cleared
        prefetched = await consumer.getmany(timeout_ms=500)
        with suppress(StopIteration):
            records = next(iter(prefetched.values()))
            assert len(records) == num_records_remaining
            for record in records:
                assert record.topic not in cleared_topics
