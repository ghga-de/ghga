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

"""Test that the work package service consumes and processes events properly."""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec

from wps.config import Config
from wps.core.models import ResearchDataUploadBox, _ResearchDataUploadBox
from wps.prepare import Consumer, prepare_consumer

from .fixtures import (  # noqa: F401
    fixture_config,
    fixture_repository,
)
from .fixtures.datasets import DATASET, DATASET_DELETION_EVENT, DATASET_UPSERTION_EVENT

pytestmark = pytest.mark.asyncio()


TIMEOUT = 10
RETRY_INTERVAL = 0.05
RETRIES = round(TIMEOUT / RETRY_INTERVAL)


@pytest_asyncio.fixture(name="consumer")
async def consumer(config: Config) -> AsyncGenerator[Consumer]:
    """Get a consumer object."""
    async with prepare_consumer(config=config) as consumer:
        yield consumer


async def test_dataset_registration(
    config: Config,
    kafka: KafkaFixture,
    consumer: Consumer,
    mongodb: MongoDbFixture,
):
    """Test the registration of a dataset announced as an event."""
    repository, subscriber = consumer

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


async def test_dataset_update(
    config: Config,
    kafka: KafkaFixture,
    consumer: Consumer,
    mongodb_populated: MongoDbFixture,
):
    """Test updating a dataset via an event."""
    repository, subscriber = consumer

    # make sure that in the beginning the dataset exists
    dataset = await repository.get_dataset("some-dataset-id")
    assert dataset.id == "some-dataset-id"
    assert dataset.title == "Test dataset 1"

    # update the dataset

    updated_dataset = DATASET_UPSERTION_EVENT
    updated_dataset = updated_dataset.model_copy(update={"title": "Changed dataset 1"})
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
        dataset = await repository.get_dataset(dataset.id)
        if dataset.title == "Changed dataset 1":
            break
    else:
        assert False, "dataset title not changed"


async def test_dataset_deletion(
    config: Config,
    kafka: KafkaFixture,
    consumer: Consumer,
    mongodb_populated: MongoDbFixture,
):
    """Test deleting a dataset via an event."""
    repository, subscriber = consumer

    # make sure that in the beginning the dataset exists
    dataset = await repository.get_dataset("some-dataset-id")
    assert dataset.id == "some-dataset-id"

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
            await repository.get_dataset(dataset.id)
        except repository.DatasetNotFoundError:
            break
    else:
        assert False, "dataset not deleted"


async def test_event_subscriber_dlq(
    config: Config,
    kafka: KafkaFixture,
    consumer: Consumer,
):
    """Verify that if we get an error when consuming an event, it gets published to the DLQ."""
    assert config.kafka_enable_dlq

    # Publish an event with a bogus payload to a topic/type this service expects
    await kafka.publish_event(
        payload={"some_key": "some_value"},
        topic=config.dataset_change_topic,
        type_=config.dataset_upsertion_type,
        key="test-key",
    )

    # Consume the event, which should error and get sent to the DLQ
    async with kafka.record_events(in_topic=config.kafka_dlq_topic) as recorder:
        await consumer.event_subscriber.run(forever=False)
    assert recorder.recorded_events
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.key == "test-key"
    assert event.payload == {"some_key": "some_value"}


async def test_consume_from_retry(
    config: Config,
    kafka: KafkaFixture,
    consumer: Consumer,
    mongodb: MongoDbFixture,
):
    """Verify that this service will correctly get events from the retry topic"""
    assert config.kafka_enable_dlq

    repository, subscriber = consumer

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

    # Check that WPS got the event from the retry topic and was able to process it
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


async def test_outbox_consumer(config: Config, kafka: KafkaFixture):
    """Test consuming an 'upserted' & 'deleted' upload box event in the outbox consumer."""
    # Create a test upload box
    research_data_upload_box_id = uuid4()
    file_upload_box_id = uuid4()
    test_event = _ResearchDataUploadBox(
        id=research_data_upload_box_id,
        title="Test Upload Box",
        description="A test upload box for testing outbox events",
        state="open",  # type: ignore
        file_upload_box_id=file_upload_box_id,
        storage_alias="test",
        changed_by=uuid4(),
        last_changed=now_utc_ms_prec(),
    )

    test_box = ResearchDataUploadBox(
        id=research_data_upload_box_id,
        file_upload_box_id=file_upload_box_id,
        title=test_event.title,
        description=test_event.description,
    )

    # Create a mock repository to track calls
    mock_repository = AsyncMock()

    # Create a consumer with the mock repository
    async with prepare_consumer(
        config=config, work_package_repo_override=mock_repository
    ) as consumer:
        subscriber = consumer.event_subscriber

        # Publish an outbox 'upserted' event for upload box
        await kafka.publish_event(
            payload=test_event.model_dump(mode="json"),
            topic=config.upload_box_topic,
            type_="upserted",
            key=str(research_data_upload_box_id),
        )

        # Process the event
        await asyncio.wait_for(subscriber.run(forever=False), timeout=TIMEOUT)

        # Verify that register_upload_box was called with the correct upload box
        mock_repository.register_upload_box.assert_called_once_with(upload_box=test_box)

        # Publish an outbox 'deleted' event
        await kafka.publish_event(
            payload={},
            topic=config.upload_box_topic,
            type_="deleted",
            key=str(research_data_upload_box_id),
        )

        # Process the event
        await asyncio.wait_for(subscriber.run(forever=False), timeout=TIMEOUT)

        # Verify that delete_upload_box was called with the correct upload box ID
        mock_repository.delete_upload_box.assert_called_once_with(
            research_data_upload_box_id
        )
