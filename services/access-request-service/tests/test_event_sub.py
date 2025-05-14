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
#

"""Test that the access request service consumes and processes events properly."""

import asyncio

import pytest

from .fixtures import ConsumerFixture
from .fixtures.datasets import DATASET, DATASET_DELETION_EVENT, DATASET_UPSERTION_EVENT

pytestmark = pytest.mark.asyncio()


TIMEOUT = 10
RETRY_INTERVAL = 0.05
RETRIES = round(TIMEOUT / RETRY_INTERVAL)


async def test_dataset_registration(consumer: ConsumerFixture):
    """Test the registration of a dataset announced as an event."""
    config = consumer.config
    kafka = consumer.kafka
    repository = consumer.repository
    subscriber = consumer.subscriber

    # make sure that in the beginning the database is empty
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.get_dataset("some-dataset-id")

    # register a dataset by publishing an event
    await kafka.publish_event(
        payload=DATASET_UPSERTION_EVENT.model_dump(),
        topic=config.dataset_change_topic,
        type_=config.dataset_upsertion_type,
        key="test-key",
    )
    # wait until the event is processed
    await asyncio.wait_for(subscriber.run(forever=False), timeout=TIMEOUT)

    # now this dataset should be retrievable
    dataset = None
    for _ in range(RETRIES):
        await asyncio.sleep(RETRY_INTERVAL)
        try:
            dataset = await repository.get_dataset("some-dataset-id")
        except repository.DatasetNotFoundError:
            pass
        else:
            assert dataset == DATASET
            break
    else:
        assert False, "dataset cannot be retrieved"

    # but another dataset should not be retrievable
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.get_dataset("another-dataset-id")


async def test_dataset_update(consumer: ConsumerFixture):
    """Test updating a dataset via an event."""
    config = consumer.config
    kafka = consumer.kafka
    repository = consumer.repository
    subscriber = consumer.subscriber

    # make sure that in the beginning the dataset exists
    await repository.register_dataset(DATASET)

    # update the dataset

    updated_dataset = DATASET_UPSERTION_EVENT
    updated_dataset = updated_dataset.model_copy(update={"title": "New title"})
    await kafka.publish_event(
        payload=updated_dataset.model_dump(),
        topic=config.dataset_change_topic,
        type_=config.dataset_upsertion_type,
        key="test-key",
    )
    await asyncio.wait_for(subscriber.run(forever=False), timeout=TIMEOUT)
    # wait until dataset is updated
    for _ in range(RETRIES):
        await asyncio.sleep(RETRY_INTERVAL)
        dataset = await repository.get_dataset(DATASET.id)
        if dataset.title == "New title":
            break
    else:
        assert False, "dataset title not changed"


async def test_dataset_deletion(consumer: ConsumerFixture):
    """Test deleting a dataset via an event."""
    config = consumer.config
    kafka = consumer.kafka
    repository = consumer.repository
    subscriber = consumer.subscriber

    # make sure that in the beginning the dataset exists
    await repository.register_dataset(DATASET)

    # delete the dataset again
    deleted_dataset = DATASET_DELETION_EVENT
    await kafka.publish_event(
        payload=deleted_dataset.model_dump(),
        topic=config.dataset_change_topic,
        type_=config.dataset_deletion_type,
        key="test-key",
    )
    await asyncio.wait_for(subscriber.run(forever=False), timeout=TIMEOUT)

    # wait until dataset is deleted
    for _ in range(RETRIES):
        await asyncio.sleep(RETRY_INTERVAL)
        try:
            await repository.get_dataset(DATASET.id)
        except repository.DatasetNotFoundError:
            break
    else:
        assert False, "dataset not deleted"


async def test_event_subscriber_dlq(consumer: ConsumerFixture):
    """Verify that if we get an error when consuming an event, it gets published to the DLQ."""
    config = consumer.config
    assert config.kafka_enable_dlq
    kafka = consumer.kafka
    subscriber = consumer.subscriber

    # Publish an event with a bogus payload to a topic/type this service expects
    await kafka.publish_event(
        payload={"some_key": "some_value"},
        topic=config.dataset_change_topic,
        type_=config.dataset_upsertion_type,
        key="test-key",
    )

    # Consume the event, which should error and get sent to the DLQ
    async with kafka.record_events(in_topic=config.kafka_dlq_topic) as recorder:
        await asyncio.wait_for(subscriber.run(forever=False), timeout=TIMEOUT)
    assert recorder.recorded_events
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.key == "test-key"
    assert event.payload == {"some_key": "some_value"}


async def test_consume_from_retry(consumer: ConsumerFixture):
    """Verify that this service will correctly get events from the retry topic"""
    config = consumer.config
    assert config.kafka_enable_dlq
    kafka = consumer.kafka
    repository = consumer.repository
    subscriber = consumer.subscriber

    # make sure that in the beginning the database is empty
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.get_dataset("some-dataset-id")

    # Publish an event with a proper payload to a topic/type this service expects
    await kafka.publish_event(
        payload=DATASET_UPSERTION_EVENT.model_dump(),
        type_=config.dataset_upsertion_type,
        topic="retry-" + config.service_name,
        key="test-key",
        headers={"original_topic": config.dataset_change_topic},
    )

    # wait until the event is processed
    await asyncio.wait_for(subscriber.run(forever=False), timeout=TIMEOUT)

    # Check that subscriber got event from retry topic and was able to process it
    dataset = None
    for _ in range(RETRIES):
        await asyncio.sleep(RETRY_INTERVAL)
        try:
            dataset = await repository.get_dataset("some-dataset-id")
        except repository.DatasetNotFoundError:
            pass
        else:
            assert dataset == DATASET
            break
    else:
        assert False, "dataset cannot be retrieved"
