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

"""Testing for the republish functionality."""

import pytest
from ghga_event_schemas.pydantic_ import FileDeletionRequested
from hexkit.correlation import get_correlation_id, set_new_correlation_id
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.providers.akafka import KafkaOutboxSubscriber
from hexkit.providers.akafka.testutils import ExpectedEvent
from hexkit.providers.mongokafka.provider import dto_to_document

from pcs.config import Config
from tests_pcs.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()


class DummySubTranslator(DaoSubscriberProtocol):
    """A class that consumes FileDeletionRequested events."""

    event_topic: str = ""
    dto_model = FileDeletionRequested
    consumed_events: list[tuple[str, str]]  # correlation ID, resource ID

    def __init__(self, *, config: Config) -> None:
        self.event_topic = config.files_to_delete_topic
        self.consumed_events = []

    async def changed(self, resource_id: str, update: FileDeletionRequested) -> None:
        """Consume event and record correlation ID"""
        self.consumed_events.append((get_correlation_id(), resource_id))

    async def deleted(self, resource_id: str) -> None:
        """Dummy"""
        raise NotImplementedError()


async def test_partial_publish(joint_fixture: JointFixture):
    """Make sure the partial publish only publishes pending events."""
    mongodb = joint_fixture.mongo_kafka.mongodb
    db = mongodb.client.get_database(joint_fixture.config.db_name)
    collection = db[joint_fixture.config.file_deletions_collection]
    published_event = FileDeletionRequested(file_id="published_event")
    unpublished_event = FileDeletionRequested(file_id="unpublished_event")

    expected_published = ExpectedEvent(
        payload=published_event.model_dump(), type_="upserted", key="published_event"
    )

    # Publish and verify the 'published' event
    async with set_new_correlation_id():
        async with joint_fixture.kafka.expect_events(
            events=[expected_published],
            in_topic=joint_fixture.config.files_to_delete_topic,
        ):
            await joint_fixture.dao.insert(published_event)

    # Insert the unpublished event manually
    async with set_new_correlation_id():
        document = dto_to_document(unpublished_event, id_field="file_id")
        collection.insert_one(document)

    expected_unpublished = ExpectedEvent(
        payload=unpublished_event.model_dump(),
        type_="upserted",
        key="unpublished_event",
    )

    # Verify that only the unpublished event is published
    async with joint_fixture.kafka.expect_events(
        events=[expected_unpublished],
        in_topic=joint_fixture.config.files_to_delete_topic,
    ):
        await joint_fixture.dao.publish_pending()


async def test_republish(joint_fixture: JointFixture):
    """Ensure the (re)publish with the configured DAO will work.

    Check that the event is republished with the correct correlation ID.
    """
    events: list[tuple[str, str]] = []  # correlation ID, resource ID
    file_ids: list[str] = ["test_id1", "test_id2"]

    for file_id in file_ids:
        file_deletion = FileDeletionRequested(file_id=file_id)
        payload = file_deletion.model_dump()
        event = ExpectedEvent(payload=payload, type_="upserted", key=file_id)

        # Publish one event at a time and verify
        async with set_new_correlation_id():
            events.append((get_correlation_id(), file_id))
            async with joint_fixture.kafka.expect_events(
                events=[event], in_topic=joint_fixture.config.files_to_delete_topic
            ):
                await joint_fixture.dao.insert(file_deletion)

    # Republish under new correlation ID to ensure it doesn't pollute the action
    async with set_new_correlation_id():
        await joint_fixture.dao.republish()

        # consume the republished events with the dummy translator
        translator = DummySubTranslator(config=joint_fixture.config)
        async with KafkaOutboxSubscriber.construct(
            config=joint_fixture.config, translators=[translator]
        ) as subscriber:
            await subscriber.run(forever=False)
            await subscriber.run(forever=False)

        # verify that the correlation IDs match what we expect. Sort first
        translator.consumed_events.sort()
        events.sort()
        assert translator.consumed_events == events
