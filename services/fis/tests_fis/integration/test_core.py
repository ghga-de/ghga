# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Integration tests for the core"""

import logging

import pytest
from hexkit.utils import now_utc_ms_prec
from pytest_httpx import HTTPXMock

from fis.core import models
from fis.ports.outbound.dao import ResourceNotFoundError
from tests_fis.fixtures.joint import JointFixture
from tests_fis.fixtures.utils import create_file_under_interrogation

pytestmark = pytest.mark.asyncio


async def test_typical_journey(joint_fixture: JointFixture, httpx_mock: HTTPXMock):
    """Test the typical path of receiving a FileUpload event through archival."""
    # Create a FileUnderInterrogation and publish it to the file uploads topic
    file = create_file_under_interrogation("HUB1")
    file.state = "inbox"
    topic = joint_fixture.config.file_upload_topic
    await joint_fixture.kafka.publish_event(
        payload=file.model_dump(),
        type_="upserted",
        topic=topic,
        key=str(file.id),
    )

    # Consume the file upload event
    await joint_fixture.outbox_consumer.run(forever=False)

    # Verify that the file was stored in the database
    _ = await joint_fixture.file_dao.get_by_id(file.id)

    # Get a list of files for hub1 that need to be interrogated
    files_to_interrogate = (
        await joint_fixture.interrogation_handler.get_files_not_yet_interrogated(
            storage_alias="HUB1"
        )
    )
    assert len(files_to_interrogate) == 1
    assert files_to_interrogate[0].id == file.id

    # Prepare mock response for EKSS call
    ekss_url = f"{joint_fixture.config.ekss_api_url}/secrets"
    secret_id = "some-secret-id"
    httpx_mock.add_response(
        url=ekss_url, method="POST", status_code=201, json={"secret_id": secret_id}
    )

    # Submit a successful interrogation report and check for the published event
    interrogation_topic = joint_fixture.config.file_interrogations_topic
    async with joint_fixture.kafka.record_events(
        in_topic=interrogation_topic
    ) as recorder:
        success_report = models.InterrogationReportWithSecret(
            file_id=file.id,
            storage_alias=file.storage_alias,
            bucket_id="interrogation1",
            object_id=file.object_id,
            interrogated_at=now_utc_ms_prec(),
            passed=True,
            secret=b"secret_data_here",
            encrypted_parts_md5=["abc123", "def456"],
            encrypted_parts_sha256=["sha256_1", "sha256_2"],
            encrypted_size=1234,
        )
        await joint_fixture.interrogation_handler.handle_interrogation_report(
            report=success_report
        )

    # Verify the interrogation success event was published
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.type_ == "interrogation_success"
    assert event.payload["file_id"] == str(file.id)
    assert event.payload["secret_id"] == secret_id

    # Verify that the file in the database now says "interrogated"
    file_in_db = await joint_fixture.file_dao.get_by_id(file.id)
    assert file_in_db.interrogated
    assert file_in_db.state == "interrogated"

    # Verify that calling the 'new uploads' endpoint returns an empty list
    assert (
        await joint_fixture.interrogation_handler.get_files_not_yet_interrogated(
            storage_alias="HUB1"
        )
    ) == []

    # Publish a File Upload event that indicates the file was archived
    archived_file = file.model_copy()
    archived_file.state = "archived"
    archived_file.state_updated = now_utc_ms_prec()
    await joint_fixture.kafka.publish_event(
        payload=archived_file.model_dump(),
        type_="upserted",
        topic=topic,
        key=str(file.id),
    )

    # Consume the archived event
    await joint_fixture.outbox_consumer.run(forever=False)

    # Verify that the file in the database now says "archived" and can_remove = True
    file_in_db = await joint_fixture.file_dao.get_by_id(file.id)
    assert file_in_db.can_remove
    assert file_in_db.interrogated  # triple check that this wasn't overwritten to False
    assert file_in_db.state == "archived"

    # Assert that check_if_removable() returns True for this file
    can_remove = await joint_fixture.interrogation_handler.check_if_removable(
        object_id=file.object_id
    )
    assert can_remove is True


@pytest.mark.parametrize(
    "state,expected_log_level,expected_msg_fragment",
    [
        ("cancelled", logging.INFO, "before the upload was finished"),
        ("failed", logging.INFO, "before the upload was finished"),
        ("interrogated", logging.WARNING, "This is unexpected"),
        ("awaiting_archival", logging.WARNING, "This is unexpected"),
        ("archived", logging.WARNING, "This is unexpected"),
    ],
)
async def test_failure_before_inbox(
    joint_fixture: JointFixture,
    caplog,
    state,
    expected_log_level,
    expected_msg_fragment,
):
    """Ensure FIS properly handles FileUpload events whose state skipped 'inbox'.

    For 'cancelled' and 'failed', this is an expected edge case (the upload failed
    before it was ever staged). For 'interrogated', 'awaiting_archival', and
    'archived', it is unexpected but should still be handled gracefully (log +
    ignore rather than raise).

    The test publishes an 'init' event (which FIS ignores and does not store) and
    then a second event with the target state. It verifies that:
    - no record was ever written to the DB for the file
    - the appropriate log message was emitted at the correct level
    """
    file = create_file_under_interrogation("HUB1")
    file.state = "init"
    topic = joint_fixture.config.file_upload_topic
    await joint_fixture.kafka.publish_event(
        payload=file.model_dump(),
        type_="upserted",
        topic=topic,
        key=str(file.id),
    )

    # Consume the init file upload event — FIS should ignore it
    await joint_fixture.outbox_consumer.run(forever=False)

    file.state = state
    await joint_fixture.kafka.publish_event(
        payload=file.model_dump(),
        type_="upserted",
        topic=topic,
        key=str(file.id),
    )

    with caplog.at_level(expected_log_level, logger="fis.core.interrogation"):
        await joint_fixture.outbox_consumer.run(forever=False)

    # The file should never have been written to the DB
    with pytest.raises(ResourceNotFoundError):
        await joint_fixture.file_dao.get_by_id(file.id)

    # Verify the expected log message was emitted at the right level
    assert any(
        record.levelno == expected_log_level and expected_msg_fragment in record.message
        for record in caplog.records
    )
