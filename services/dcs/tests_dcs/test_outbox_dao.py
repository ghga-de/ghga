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
"""Tests for the outbox (mongokafka) dao publisher."""

from unittest.mock import AsyncMock

import pytest
from ghga_event_schemas.pydantic_ import NonStagedFileRequested
from hexkit.correlation import get_correlation_id, set_new_correlation_id
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.providers.akafka import KafkaOutboxSubscriber
from hexkit.providers.akafka.testutils import ExpectedEvent
from hexkit.providers.mongokafka.provider import dto_to_document

from dcs.config import Config
from dcs.inject import get_nonstaged_file_requested_dao
from tests_dcs.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()
CHANGED = "upserted"


def make_test_event(file_id: str) -> NonStagedFileRequested:
    """Return a FileUploadReceived event with the given file ID."""
    event = NonStagedFileRequested(
        file_id=file_id,
        target_object_id="test_target_object_id",
        target_bucket_id="test_target_bucket_id",
        s3_endpoint_alias="test_s3_endpoint_alias",
        decrypted_sha256="test_decrypted_sha256",
    )
    return event


async def test_dto_to_event(joint_fixture: JointFixture):
    """Make sure the dto_to_event piece of the mongokafka dao is set up right.

    The expected payload is a NonStagedFileRequested model dump.
    """
    config = joint_fixture.config
    async with get_nonstaged_file_requested_dao(config=config) as outbox_dao:
        dto = make_test_event(file_id="test123")

        expected_event = ExpectedEvent(
            payload=dto.model_dump(), type_=CHANGED, key=dto.file_id
        )

        async with (
            set_new_correlation_id(),
            joint_fixture.kafka.expect_events(
                events=[expected_event],
                in_topic=config.unstaged_download_event_topic,
            ),
        ):
            await outbox_dao.upsert(dto)


class DummySubTranslator(DaoSubscriberProtocol):
    """A class that consumes NonStagedFileRequested events."""

    event_topic: str = ""
    dto_model = NonStagedFileRequested
    consumed_events: list[tuple[str, str]]  # correlation ID, resource ID

    def __init__(self, *, config: Config) -> None:
        self.event_topic = config.unstaged_download_event_topic
        self.consumed_events = []

    async def changed(self, resource_id: str, update: NonStagedFileRequested) -> None:
        """Consume event and record correlation ID"""
        self.consumed_events.append((get_correlation_id(), resource_id))

    async def deleted(self, resource_id: str) -> None:
        """Dummy"""
        raise NotImplementedError()


async def test_partial_publish(joint_fixture: JointFixture):
    """Make sure the partial publish only publishes pending events."""
    db = joint_fixture.mongodb.client.get_database(joint_fixture.config.db_name)
    collection = db[joint_fixture.config.unstaged_download_collection]
    published_event = make_test_event(file_id="published_event")
    unpublished_event = make_test_event(file_id="unpublished_event")

    expected_published = ExpectedEvent(
        payload=published_event.model_dump(), type_=CHANGED, key="published_event"
    )

    # Publish and verify the 'published' event
    async with set_new_correlation_id():
        async with joint_fixture.kafka.expect_events(
            events=[expected_published],
            in_topic=joint_fixture.config.unstaged_download_event_topic,
        ):
            await joint_fixture.nonstaged_file_requested_dao.insert(published_event)

    # Insert the unpublished event manually
    async with set_new_correlation_id():
        document = dto_to_document(unpublished_event, id_field="file_id")
        collection.insert_one(document)

    expected_unpublished = ExpectedEvent(
        payload=unpublished_event.model_dump(),
        type_=CHANGED,
        key="unpublished_event",
    )

    # Verify that only the unpublished event is published
    async with joint_fixture.kafka.expect_events(
        events=[expected_unpublished],
        in_topic=joint_fixture.config.unstaged_download_event_topic,
    ):
        await joint_fixture.nonstaged_file_requested_dao.publish_pending()


async def test_republish(joint_fixture: JointFixture):
    """Ensure the republish command on the DAO will work.

    Check that the event is republished with the correct correlation ID.
    """
    events: list[tuple[str, str]] = []  # correlation ID, resource ID
    file_ids: list[str] = ["test_id1", "test_id2"]

    for file_id in file_ids:
        file_deletion = make_test_event(file_id=file_id)
        payload = file_deletion.model_dump()
        event = ExpectedEvent(payload=payload, type_=CHANGED, key=file_id)

        # Publish one event at a time and verify
        async with set_new_correlation_id():
            events.append((get_correlation_id(), file_id))
            async with joint_fixture.kafka.expect_events(
                events=[event],
                in_topic=joint_fixture.config.unstaged_download_event_topic,
            ):
                await joint_fixture.nonstaged_file_requested_dao.insert(file_deletion)

    # Clear the topics to ensure we don't get any old events
    await joint_fixture.kafka.clear_topics()

    # Republish under new correlation ID to ensure it doesn't pollute the action
    async with set_new_correlation_id():
        await joint_fixture.nonstaged_file_requested_dao.republish()

        # consume the republished events with the dummy translator
        translator = DummySubTranslator(config=joint_fixture.config)
        async with KafkaOutboxSubscriber.construct(
            config=joint_fixture.config,
            translators=[translator],
            dlq_publisher=AsyncMock(),
        ) as subscriber:
            await subscriber.run(forever=False)
            await subscriber.run(forever=False)

        # verify that the correlation IDs match what we expect. Sort first
        translator.consumed_events.sort()
        events.sort()
        assert translator.consumed_events == events
