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

"""Fixtures for handling events."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from metldata.event_handling.event_handling import (
    Event,
    FileSystemEventCollector,
    FileSystemEventConfig,
    FileSystemEventPublisher,
)


class EventExpectationMissmatch(RuntimeError):
    """Raised when expected events where not found."""

    def __init__(self, expected_events: set[str], consumed_events: set[str]):
        message = f"Expected events '{expected_events}' but got '{consumed_events}'"
        super().__init__(message)


@dataclass
class FileSystemEventFixture:
    """Returned by file_system_event_fixture."""

    config: FileSystemEventConfig
    publisher: FileSystemEventPublisher
    collector: FileSystemEventCollector

    def expect_events(self, expected_events: list[Event]) -> None:
        """Check if the events expected to be published can be consumed.

        Raises:
            EventExpectationMissmatch: If the expected events are not consumed.
        """

        topics = sorted({event.topic for event in expected_events})
        types = sorted({event.type_ for event in expected_events})

        observed_events: list[Event] = []
        for topic in topics:
            observed_events.extend(
                self.collector.collect_events(topic=topic, types=types)
            )

        # hashable versions for comparison:
        observed_event_jsons = {event.json() for event in observed_events}
        expected_event_jsons = {event.json() for event in expected_events}

        if expected_event_jsons != observed_event_jsons:
            raise EventExpectationMissmatch(
                expected_events=observed_event_jsons,
                consumed_events=expected_event_jsons,
            )

    async def publish_events(self, events: list[Event]) -> None:
        """Publish a list of events."""

        for event in events:
            await self.publisher.publish(
                topic=event.topic,
                type_=event.type_,
                key=event.key,
                payload=event.payload,
            )


@pytest.fixture
def file_system_event_fixture(tmp_path: Path) -> FileSystemEventFixture:
    """A fixture for handling events on the file system."""

    config = FileSystemEventConfig(
        event_store_path=tmp_path,
    )
    publisher = FileSystemEventPublisher(config=config)
    collector = FileSystemEventCollector(config=config)
    return FileSystemEventFixture(
        config=config, publisher=publisher, collector=collector
    )
