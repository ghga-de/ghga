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

import pytest
from ghga_event_schemas.pydantic_ import FileUploadValidationSuccess
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.correlation import get_correlation_id, set_new_correlation_id
from hexkit.protocols.daosub import DaoSubscriberProtocol
from hexkit.providers.akafka import KafkaOutboxSubscriber
from hexkit.providers.akafka.testutils import ExpectedEvent
from hexkit.providers.mongokafka.provider import dto_to_document

from fis.config import Config
from fis.inject import get_file_validation_success_dao
from tests_fis.fixtures.joint import TEST_PAYLOAD, JointFixture

pytestmark = pytest.mark.asyncio()


def make_test_event(file_id: str) -> FileUploadValidationSuccess:
    """Return a FileUploadValidationSuccess event with the given file ID."""
    event = FileUploadValidationSuccess(
        upload_date=now_as_utc().isoformat(),
        file_id=file_id,
        object_id="",
        bucket_id="",
        s3_endpoint_alias="",
        decrypted_size=0,
        decryption_secret_id="",
        content_offset=0,
        encrypted_part_size=0,
        encrypted_parts_md5=[],
        encrypted_parts_sha256=[],
        decrypted_sha256="",
    )
    return event


async def test_dto_to_event(joint_fixture: JointFixture):
    """Make sure the dto_to_event piece of the mongokafka dao is set up right.

    The expected event is a FileUploadValidationSuccess event.
    """
    config = joint_fixture.config
    async with get_file_validation_success_dao(config=config) as outbox_dao:
        dto = FileUploadValidationSuccess(
            upload_date=now_as_utc().isoformat(),
            file_id=TEST_PAYLOAD.file_id,
            object_id=TEST_PAYLOAD.object_id,
            bucket_id=joint_fixture.config.source_bucket_id,
            s3_endpoint_alias=joint_fixture.s3_endpoint_alias,
            decrypted_size=TEST_PAYLOAD.unencrypted_size,
            decryption_secret_id="",
            content_offset=0,
            encrypted_part_size=TEST_PAYLOAD.part_size,
            encrypted_parts_md5=TEST_PAYLOAD.encrypted_md5_checksums,
            encrypted_parts_sha256=TEST_PAYLOAD.encrypted_sha256_checksums,
            decrypted_sha256=TEST_PAYLOAD.unencrypted_checksum,
        )

        expected_event = ExpectedEvent(
            payload=dto.model_dump(), type_="upserted", key=dto.file_id
        )

        async with (
            set_new_correlation_id(),
            joint_fixture.kafka.expect_events(
                events=[expected_event],
                in_topic=config.file_upload_validation_success_topic,
            ),
        ):
            await outbox_dao.upsert(dto)


class DummySubTranslator(DaoSubscriberProtocol):
    """A class that consumes FileUploadValidationSuccess events."""

    event_topic: str = ""
    dto_model = FileUploadValidationSuccess
    consumed_events: list[tuple[str, str]]  # correlation ID, resource ID

    def __init__(self, *, config: Config) -> None:
        self.event_topic = config.file_upload_validation_success_topic
        self.consumed_events = []

    async def changed(
        self, resource_id: str, update: FileUploadValidationSuccess
    ) -> None:
        """Consume event and record correlation ID"""
        self.consumed_events.append((get_correlation_id(), resource_id))

    async def deleted(self, resource_id: str) -> None:
        """Dummy"""
        raise NotImplementedError()


async def test_partial_publish(joint_fixture: JointFixture):
    """Make sure the partial publish only publishes pending events."""
    db = joint_fixture.mongodb.client.get_database(joint_fixture.config.db_name)
    collection = db[joint_fixture.config.file_validations_collection]
    published_event = make_test_event(file_id="published_event")
    unpublished_event = make_test_event(file_id="unpublished_event")

    expected_published = ExpectedEvent(
        payload=published_event.model_dump(), type_="upserted", key="published_event"
    )

    # Publish and verify the 'published' event
    async with set_new_correlation_id():
        async with joint_fixture.kafka.expect_events(
            events=[expected_published],
            in_topic=joint_fixture.config.file_upload_validation_success_topic,
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
        in_topic=joint_fixture.config.file_upload_validation_success_topic,
    ):
        await joint_fixture.dao.publish_pending()


async def test_republish(joint_fixture: JointFixture):
    """Ensure the republish command on the DAO will work.

    Check that the event is republished with the correct correlation ID.
    """
    events: list[tuple[str, str]] = []  # correlation ID, resource ID
    file_ids: list[str] = ["test_id1", "test_id2"]

    for file_id in file_ids:
        file_deletion = make_test_event(file_id=file_id)
        payload = file_deletion.model_dump()
        event = ExpectedEvent(payload=payload, type_="upserted", key=file_id)

        # Publish one event at a time and verify
        async with set_new_correlation_id():
            events.append((get_correlation_id(), file_id))
            async with joint_fixture.kafka.expect_events(
                events=[event],
                in_topic=joint_fixture.config.file_upload_validation_success_topic,
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
