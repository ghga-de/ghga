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
#

"""Test that the work package service consumes and processes events properly."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from hexkit.providers.akafka.testutils import KafkaFixture

from wps.config import Config
from wps.inject import Consumer, prepare_consumer

from .fixtures import (  # noqa: F401
    fixture_config,
    fixture_repository,
)
from .fixtures.datasets import DATASET, DATASET_DELETION_EVENT, DATASET_UPSERTION_EVENT

pytestmark = pytest.mark.asyncio(scope="session")


TIMEOUT = 10
RETRY_INTERVAL = 0.05
RETRIES = round(TIMEOUT / RETRY_INTERVAL)


@pytest_asyncio.fixture(name="consumer", scope="session")
async def consumer(config: Config) -> AsyncGenerator[Consumer, None]:
    """Get a consumer object."""
    async with prepare_consumer(config=config) as consumer:
        yield consumer


async def test_dataset_registration(
    config: Config,
    kafka_fixture: KafkaFixture,
    consumer: Consumer,
    empty_mongodb,
):
    """Test the registration of a dataset announced as an event."""
    repository, subscriber = consumer

    # make sure that in the beginning the database is empty
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.get_dataset("some-dataset-id")

    # register a dataset by publishing an event
    await kafka_fixture.publish_event(
        payload=DATASET_UPSERTION_EVENT.model_dump(),
        topic=config.dataset_change_event_topic,
        type_=config.dataset_upsertion_event_type,
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
    config: Config, kafka_fixture: KafkaFixture, consumer: Consumer, populated_mongodb
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
    await kafka_fixture.publish_event(
        payload=updated_dataset.model_dump(),
        topic=config.dataset_change_event_topic,
        type_=config.dataset_upsertion_event_type,
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
    config: Config, kafka_fixture: KafkaFixture, consumer: Consumer, populated_mongodb
):
    """Test deleting a dataset via an event."""
    repository, subscriber = consumer

    # make sure that in the beginning the dataset exists
    dataset = await repository.get_dataset("some-dataset-id")
    assert dataset.id == "some-dataset-id"

    # delete the dataset again

    deleted_dataset = DATASET_DELETION_EVENT
    await kafka_fixture.publish_event(
        payload=deleted_dataset.model_dump(),
        topic=config.dataset_change_event_topic,
        type_=config.dataset_deletion_event_type,
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
