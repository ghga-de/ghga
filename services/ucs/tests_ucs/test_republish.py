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
"""Test the republish mechanism of the persistent publisher."""

import pytest
from hexkit.correlation import set_new_correlation_id

from tests_ucs.fixtures.joint import JointFixture
from tests_ucs.fixtures.utils import make_test_event
from ucs.inject import get_persistent_publisher

pytestmark = pytest.mark.asyncio()


async def test_republish(joint_fixture: JointFixture):
    """Make sure the partial publish only publishes pending events."""
    db = joint_fixture.mongodb.client.get_database(joint_fixture.config.db_name)
    collection = db["ucsPersistedEvents"]
    published_event = make_test_event(file_id="published_event")
    unpublished_event = make_test_event(file_id="unpublished_event")
    topic = joint_fixture.config.file_upload_received_topic
    type_ = joint_fixture.config.file_upload_received_type

    # Publish the 'published' event
    async with (
        set_new_correlation_id(),
        get_persistent_publisher(config=joint_fixture.config) as publisher,
    ):
        await publisher.publish(
            payload=published_event.model_dump(),
            topic=topic,
            type_=type_,
            key=published_event.file_id,
        )

    # Verify that the published event was saved in the collection
    docs = collection.find().to_list()
    assert len(docs) == 1
    assert docs[0]["payload"]["file_id"] == published_event.file_id
    assert docs[0]["published"]

    # Insert the unpublished event manually by copying/modifying the first one
    new_doc = {**docs[0]}
    new_doc["payload"]["file_id"] = unpublished_event.file_id
    new_doc["payload"]["upload_date"] = unpublished_event.upload_date
    new_doc["_id"] = f"{topic}:{unpublished_event.file_id}"
    new_doc["key"] = unpublished_event.file_id
    new_doc["published"] = False
    collection.insert_one(new_doc)

    # Publish pending
    async with joint_fixture.kafka.record_events(in_topic=topic) as recorder:
        async with get_persistent_publisher(config=joint_fixture.config) as publisher:
            await publisher.publish_pending()

    # Verify that only the unpublished event was published
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.payload == unpublished_event.model_dump()
    assert event.key == unpublished_event.file_id

    # Publish all events again
    async with joint_fixture.kafka.record_events(in_topic=topic) as recorder:
        async with get_persistent_publisher(config=joint_fixture.config) as publisher:
            await publisher.republish()

    # Verify that all events were republished
    assert len(recorder.recorded_events) == 2
    assert {event.key for event in recorder.recorded_events} == {
        published_event.file_id,
        unpublished_event.file_id,
    }
