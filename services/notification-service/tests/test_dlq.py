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

"""Test to make sure that the DLQ is correctly set up for this service."""

import pytest
from hexkit.providers.akafka.testutils import KafkaFixture

from ns.inject import prepare_event_subscriber
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


async def test_event_subscriber_dlq(kafka: KafkaFixture):
    """Verify that if we get an error when consuming an event, it gets published to the DLQ."""
    config = get_config(sources=[kafka.config], kafka_enable_dlq=True)
    assert config.kafka_enable_dlq

    # Publish an event with a bogus payload to a topic/type this service expects
    await kafka.publish_event(
        payload={"some_key": "some_value"},
        type_=config.notification_type,
        topic=config.notification_topic,
        key="test",
    )
    async with kafka.record_events(in_topic=config.kafka_dlq_topic) as recorder:
        # Consume the event, which should error and get sent to the DLQ
        async with prepare_event_subscriber(config=config) as event_subscriber:
            await event_subscriber.run(forever=False)
    assert recorder.recorded_events
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.key == "test"
    assert event.payload == {"some_key": "some_value"}


async def test_consume_from_retry(kafka: KafkaFixture):
    """Verify that this service will correctly get events from the retry topic"""
    config = get_config(sources=[kafka.config], kafka_enable_dlq=True)
    assert config.kafka_enable_dlq

    sample_notification = {
        "recipient_email": "test@example.com",
        "email_cc": ["test2@test.com", "test3@test.com"],
        "email_bcc": ["test4@test.com", "test5@test.com"],
        "subject": "Test123",
        "recipient_name": "Yolanda Martinez",
        "plaintext_body": "Where are you, where are you, Yolanda?",
    }

    # Publish an event with a proper payload to a topic/type this service expects
    await kafka.publish_event(
        payload=sample_notification,
        type_=config.notification_type,
        topic="retry-" + config.service_name,
        key="test",
        headers={"original_topic": config.notification_topic},
    )

    # Consume the event
    async with prepare_event_subscriber(config=config) as event_subscriber:
        await event_subscriber.run(forever=False)
