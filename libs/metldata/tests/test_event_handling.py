# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the event_handling module."""

import json

import pytest
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventsub import EventSubscriberProtocol
from pydantic import BaseModel, ConfigDict, Field

from metldata.event_handling.event_handling import FileSystemEventSubscriber
from tests.fixtures.event_handling import (
    Event,
    FileSystemEventFixture,
    file_system_event_fixture,  # noqa: F401
)

EXAMPLE_EVENTS = [
    Event(topic="topic1", type_="type1", key="key1", payload={"test1": "value1"}),
    # overwrites above event since same key:
    Event(topic="topic1", type_="type2", key="key1", payload={"test2": "value2"}),
    # other key thus will be present:
    Event(topic="topic1", type_="type1", key="key2", payload={"test3": "value3"}),
    # publish to other topic:
    Event(topic="topic2", type_="type1", key="key1", payload={"test4": "value4"}),
]


class ConsumedEvent(BaseModel):
    """Consumed event without the key."""

    model_config = ConfigDict(frozen=True)
    topic: str
    type_: str
    payload: str = Field(..., description="JSON string of the event payload.")


@pytest.mark.asyncio
async def test_pub_sub_workflow(
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test a publish subscribe workflow using the FileSystemEventPublisher and
    FileSystemEventSubscriber."""

    # expected events to consume in topic1:
    expected_events = {
        ConsumedEvent(
            topic="topic1", type_="type2", payload=json.dumps({"test2": "value2"})
        ),
        ConsumedEvent(
            topic="topic1", type_="type1", payload=json.dumps({"test3": "value3"})
        ),
    }

    # publish events:
    await file_system_event_fixture.publish_events(EXAMPLE_EVENTS)

    # use event subscriber to consume events:
    class MockSubscriberTranslator(EventSubscriberProtocol):
        """A mock implementation of the EventSubscriberProtocol to track consumed
        events. Only consumes from topic1.

        Consumed events are captured in the consumed_events attribute.
        """

        def __init__(self):
            self.consumed_events: set[ConsumedEvent] = set()
            self.topics_of_interest = {"topic1"}
            self.types_of_interest = {"type1", "type2"}

        async def _consume_validated(
            self, *, payload: JsonObject, type_: Ascii, topic: Ascii
        ) -> None:
            self.consumed_events.add(
                ConsumedEvent(topic=topic, type_=type_, payload=json.dumps(payload))
            )

    translator = MockSubscriberTranslator()
    subscriber = FileSystemEventSubscriber(
        config=file_system_event_fixture.config, translator=translator
    )
    await subscriber.run()

    # check consumed events:
    assert translator.consumed_events == expected_events


@pytest.mark.asyncio
async def test_pub_collect_workflow(
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test a publish collect workflow using the FileSystemEventPublisher and
    FileSystemEventCollector."""

    expected_events = EXAMPLE_EVENTS.copy()
    del expected_events[0]  # remove event with same key

    # publish events:
    await file_system_event_fixture.publish_events(EXAMPLE_EVENTS)

    # check published events with collector:
    file_system_event_fixture.expect_events(expected_events)
