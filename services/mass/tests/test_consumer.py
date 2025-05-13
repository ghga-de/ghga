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

"""Tests to verify functionality of kafka event consumer"""

from unittest.mock import AsyncMock

import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.akafka.testutils import KafkaFixture

from mass.core import models
from mass.inject import prepare_event_subscriber
from tests.fixtures.config import get_config
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()

CLASS_NAME = "NestedData"


@pytest.mark.parametrize(
    "resource_id,is_insert",
    [
        ("added-resource", True),  # this is a new ID
        ("1HotelAlpha-id", False),  # this ID exists in the test data already
    ],
)
async def test_resource_upsert(
    joint_fixture: JointFixture, resource_id: str, is_insert: bool
):
    """Try upserting with no pre-existing resource with matching ID (i.e. insert)"""
    # get all the documents in the collection
    results_all = await joint_fixture.handle_query(class_name=CLASS_NAME)
    assert results_all.count > 0

    # define content of resource
    content: dict = {
        "object": {"type": "added-resource-object", "id": "98u44-f4jo4"},
        "city": "something",
        "category": "test object",
    }

    # define a resource to be upserted
    resource = models.Resource(id_=resource_id, content=content)

    # put together event payload
    payload = event_schemas.SearchableResource(
        accession=resource_id,
        class_name=CLASS_NAME,
        content=content,
    ).model_dump()

    # publish the event
    await joint_fixture.publish_event(
        payload=payload,
        type_=joint_fixture.config.resource_upsertion_type,
        topic=joint_fixture.config.resource_change_topic,
        key=f"dataset_embedded_{resource_id}",
    )

    # consume the event
    await joint_fixture.consume_event()

    # verify that the resource was added
    updated_resources = await joint_fixture.handle_query(class_name=CLASS_NAME)
    if is_insert:
        assert updated_resources.count - results_all.count == 1
    else:
        assert updated_resources.count == results_all.count

    # remove unselected fields
    content = resource.content  # type: ignore
    del content["city"]
    del content["category"]
    del content["object"]["id"]

    assert resource in updated_resources.hits
    assert resource not in results_all.hits


async def test_resource_delete(joint_fixture: JointFixture):
    """Test resource deletion via event consumption"""
    # get all the documents in the collection
    targeted_initial_results = await joint_fixture.handle_query(
        class_name=CLASS_NAME, query='"1HotelAlpha-id"'
    )
    assert targeted_initial_results.count == 1
    assert targeted_initial_results.hits[0].id_ == "1HotelAlpha-id"

    resource_info = event_schemas.SearchableResourceInfo(
        accession="1HotelAlpha-id", class_name=CLASS_NAME
    )

    await joint_fixture.publish_event(
        payload=resource_info.model_dump(),
        type_=joint_fixture.config.resource_deletion_type,
        topic=joint_fixture.config.resource_change_topic,
        key=f"dataset_embedded_{resource_info.accession}",
    )

    # consume the event
    await joint_fixture.consume_event()

    # get all the documents in the collection
    results_post_delete = await joint_fixture.handle_query(
        class_name=CLASS_NAME, query='"1HotelAlpha-id"'
    )

    assert results_post_delete.count == 0


async def test_event_subscriber_dlq(joint_fixture: JointFixture):
    """Verify that if we get an error when consuming an event, it gets published to the DLQ."""
    config = joint_fixture.config
    assert config.kafka_enable_dlq

    # Publish an event with a bogus payload to a topic/type this service expects
    await joint_fixture.publish_event(
        payload={"some_key": "some_value"},
        type_=config.resource_upsertion_type,
        topic=config.resource_change_topic,
        key="test",
    )
    async with joint_fixture._kafka.record_events(
        in_topic=config.kafka_dlq_topic
    ) as recorder:
        # Consume the event, which should error and get sent to the DLQ
        await joint_fixture.consume_event()
    assert recorder.recorded_events
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.key == "test"
    assert event.payload == {"some_key": "some_value"}


async def test_consume_from_retry(kafka: KafkaFixture):
    """Verify that this service will correctly get events from the retry topic"""
    config = get_config(sources=[kafka.config], kafka_enable_dlq=True)
    assert config.kafka_enable_dlq

    # define content of resource
    content: dict = {
        "object": {"type": "added-resource-object", "id": "98u44-f4jo4"},
        "city": "something",
        "category": "test object",
    }

    # put together event payload
    payload = event_schemas.SearchableResource(
        accession="added-resource",
        class_name=CLASS_NAME,
        content=content,
    ).model_dump()

    # Publish an event with a proper payload to a topic/type this service expects
    await kafka.publish_event(
        payload=payload,
        type_=config.resource_upsertion_type,
        topic="retry-" + config.service_name,
        key="test",
        headers={"original_topic": config.resource_change_topic},
    )

    # Consume the event
    qh_mock = AsyncMock()
    async with prepare_event_subscriber(
        config=config, query_handler_override=qh_mock
    ) as consumer:
        await consumer.run(forever=False)

    qh_mock.load_resource.assert_awaited_once()
