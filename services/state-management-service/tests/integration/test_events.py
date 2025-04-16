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
"""Integration tests for the kafka state management."""

from contextlib import suppress
from typing import Any
from unittest.mock import AsyncMock

import pytest
from aiokafka import AIOKafkaConsumer
from aiokafka.admin import NewTopic
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.akafka.testutils import KafkaFixture

from sms.core.events_handler import EventsHandler
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


async def test_get_policy(kafka: KafkaFixture):
    """Verify that `_get_cleanup_policy()` returns the current value"""
    config = get_config(sources=[kafka.config])
    events_handler = EventsHandler(config=config, event_publisher=AsyncMock())
    async with events_handler.get_admin_client() as admin_client:
        # Create a Kafka topic with the cleanup policy set to 'delete'
        topic_policies = [
            ["deletion_topic", "delete"],
            ["both_topic", "compact,delete"],
            ["compact_topic", "compact"],
        ]
        new_topics = [
            NewTopic(
                name=topic,
                num_partitions=1,
                replication_factor=1,
                topic_configs={"cleanup.policy": policy},
            )
            for topic, policy in topic_policies
        ]
        await admin_client.create_topics(new_topics)

        # Check the policy for a topic that hasn't been created
        assert await events_handler._get_cleanup_policy(topic="doesnotexist") is None

        # Retrieve the cleanup policy for each of the topics we just made
        for topic, policy in topic_policies:
            assigned_policy = await events_handler._get_cleanup_policy(topic=topic)

            # Verify that the returned value is correct
            assert assigned_policy == policy


async def test_set_policy(kafka: KafkaFixture):
    """Verify that `_set_cleanup_policy()` updates the current value"""
    config = get_config(sources=[kafka.config])
    events_handler = EventsHandler(config=config, event_publisher=AsyncMock())
    async with events_handler.get_admin_client() as admin_client:
        # Create a Kafka topic with the cleanup policy set to 'compact'
        if not await events_handler._get_cleanup_policy(topic=TEST_TOPIC1):
            await admin_client.create_topics(
                [
                    NewTopic(
                        name=TEST_TOPIC1,
                        num_partitions=1,
                        replication_factor=1,
                        topic_configs={"cleanup.policy": "compact"},
                    )
                ]
            )

        # Assert that the cleanup policy is set to 'compact'
        policy_before = await events_handler._get_cleanup_policy(topic=TEST_TOPIC1)
        assert policy_before == "compact"

        # Assign the new policy
        await events_handler._set_cleanup_policy(topic=TEST_TOPIC1, policy="delete")

        # Verify that the policy was updated
        policy_after = await events_handler._get_cleanup_policy(topic=TEST_TOPIC1)
        assert policy_after == "delete"


@pytest.mark.parametrize(
    "events_to_publish",
    [
        TEST_EVENTS,
        [],
    ],
    ids=[
        "EventsPublished",
        "NoEventsPublished",
    ],
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

    # Make sure to set policy to "compact" for the topics
    events_handler = EventsHandler(config=config, event_publisher=AsyncMock())
    async with events_handler.get_admin_client() as admin_client:
        existing_topics = await admin_client.list_topics()
        for topic in topics_to_clear:
            # Create the topic if it doesn't exist already
            if topic not in existing_topics:
                await admin_client.create_topics(
                    [
                        NewTopic(
                            name=topic,
                            num_partitions=1,
                            replication_factor=1,
                            topic_configs={"cleanup.policy": "compact"},
                        )
                    ]
                )
            else:
                # If topic does exist, check the cleanup policy
                policy = await events_handler._get_cleanup_policy(topic=topic)
                assert policy
                if "compact" not in policy.split(","):
                    await events_handler._set_cleanup_policy(
                        topic=topic, policy="compact"
                    )

        # Publish events if applicable
        published_topics: set[str] = set()
        for event in events_to_publish:
            published_topics.add(event["topic"])
            await kafka.publish_event(**event)

    # Call the endpoint to CLEAR THE TOPICS specified in topics_to_clear
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

        try:
            # Get a list of the topics cleared -- an empty topics_to_clear means all topics
            # (ignore internal topics for the test)
            cleared_topics = topics_to_clear if topics_to_clear else published_topics

            # Calculate how many events should have been deleted
            deleted_event_count = sum(
                1 for event in events_to_publish if event["topic"] in cleared_topics
            )

            # Calculate how many events should remain
            num_events_remaining = len(events_to_publish) - deleted_event_count

            # Verify that the topics have been cleared
            prefetched = await consumer.getmany(timeout_ms=500)
            with suppress(StopIteration):
                records = next(iter(prefetched.values()))
                assert len(records) == num_events_remaining
                for record in records:
                    assert record.topic not in cleared_topics
        finally:
            await consumer.stop()


async def test_clear_topics_error(kafka: KafkaFixture):
    """Make sure the original cleanup policies are restored if there's an error in
    `delete_topics`.
    """
    config = get_config(sources=[kafka.config])
    events_handler = EventsHandler(config=config, event_publisher=AsyncMock())
    topic = "badthings"
    async with events_handler.get_admin_client():
        await kafka.publish_event(
            payload={"some": "cool payload"},
            type_="erroring_type",
            topic=topic,
            key="mykey",
        )
        await events_handler._set_cleanup_policy(topic=topic, policy="compact,delete")

        await events_handler.clear_topics(topics=[topic])
        assert await events_handler._get_cleanup_policy(topic=topic) == "compact,delete"


# Test event publishing
@pytest.mark.parametrize(
    "event_to_publish",
    [TEST_EVENT1, TEST_EVENT2, TEST_EVENT3],
    ids=["Event1", "Event2", "Event3"],
)
async def test_publish_event_happy(
    kafka: KafkaFixture,
    event_to_publish: dict[str, Any],
):
    """Test that events can be published."""
    config = get_config(sources=[kafka.config])

    # Call the endpoint to publish the event
    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
        kafka.record_events(in_topic=event_to_publish["topic"]) as recorder,
    ):
        response = await client.post(
            "/events/",
            json=event_to_publish,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 204
    assert recorder.recorded_events
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.payload == event_to_publish["payload"]
    assert event.type_ == event_to_publish["type_"]
    assert event.key == event_to_publish["key"]
