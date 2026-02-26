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

"""Unit tests for the core logic"""

from datetime import timedelta
from uuid import uuid4

import pytest
from hexkit.utils import now_utc_ms_prec

from fis.core import models
from fis.ports.inbound.interrogation import InterrogationHandlerPort
from fis.ports.outbound.dao import ResourceNotFoundError
from fis.ports.outbound.secrets import SecretsClientPort
from tests_fis.fixtures.joint import JointRig
from tests_fis.fixtures.utils import create_file_under_interrogation

pytestmark = pytest.mark.asyncio()

HUB1 = "HUB1"
HUB2 = "HUB2"


async def test_check_if_removable(rig: JointRig):
    """Test the `.check_if_removable()` method"""
    # A non-existent file should net us a return value of True
    file = create_file_under_interrogation(HUB1)
    assert (
        await rig.interrogation_handler.check_if_removable(object_id=file.object_id)
        == True
    )

    await rig.file_dao.insert(file)
    assert (
        await rig.interrogation_handler.check_if_removable(object_id=file.object_id)
        == False
    )

    file.can_remove = True
    await rig.file_dao.update(file)
    assert (
        await rig.interrogation_handler.check_if_removable(object_id=file.object_id)
        == True
    )


async def test_report_handling_successful(rig: JointRig):
    """Test the `.handle_interrogation_report()` method happy path"""
    file = create_file_under_interrogation(HUB1)
    success_report = models.InterrogationReportWithSecret(
        file_id=file.id,
        storage_alias=file.storage_alias,
        bucket_id="interrogation1",
        object_id=uuid4(),
        interrogated_at=now_utc_ms_prec(),
        passed=True,
        secret=b"secret_data_here",
        encrypted_parts_md5=["abc123", "def456"],
        encrypted_parts_sha256=["sha256_1", "sha256_2"],
        encrypted_size=1234,
    )

    # Verify that a report for a file we don't have triggers a FileNotFoundError
    with pytest.raises(InterrogationHandlerPort.FileNotFoundError):
        await rig.interrogation_handler.handle_interrogation_report(
            report=success_report
        )

    # Insert the test file
    assert not file.can_remove
    assert file.state not in ["interrogated", "failed"]
    await rig.file_dao.insert(file)

    secret_id = "test-secret-id-12345"
    rig.secrets_client.deposit_secret.return_value = secret_id

    # Submit the report again now that we've inserted the file
    await rig.interrogation_handler.handle_interrogation_report(report=success_report)

    # Verify deposit_secret was called with the report's secret
    rig.secrets_client.deposit_secret.assert_called_once_with(
        secret=success_report.secret
    )

    # Verify file was updated
    updated_file = await rig.file_dao.get_by_id(file.id)
    assert updated_file.interrogated is True
    assert updated_file.state == "interrogated"
    assert updated_file.can_remove is False

    # Verify the report was persisted
    stored_report = await rig.interrogation_report_dao.get_by_id(file.id)
    assert stored_report.file_id == file.id
    assert stored_report.passed is True

    # Verify event was published
    event = rig.event_store.get(rig.config.file_interrogations_topic)
    assert event.payload["file_id"] == str(file.id)
    assert event.payload["secret_id"] == secret_id
    assert event.payload["storage_alias"] == file.storage_alias
    assert event.payload["object_id"] == str(success_report.object_id)
    assert event.payload["encrypted_size"] == success_report.encrypted_size


async def test_report_handling_failure(rig: JointRig):
    """Test the `.handle_interrogation_report()` method for a failed interrogation"""
    # Create a file for failed interrogation
    file = create_file_under_interrogation(HUB1)
    await rig.file_dao.insert(file)

    # Test failed interrogation report
    failure_report = models.InterrogationReportWithSecret(
        file_id=file.id,
        storage_alias=file.storage_alias,
        interrogated_at=now_utc_ms_prec(),
        passed=False,
        reason="Checksum mismatch detected",
    )
    await rig.interrogation_handler.handle_interrogation_report(report=failure_report)

    # Verify file was updated and marked for removal
    updated_file2 = await rig.file_dao.get_by_id(file.id)
    assert updated_file2.interrogated is True
    assert updated_file2.state == "failed"
    assert updated_file2.can_remove is True

    # Verify the report was persisted
    stored_report = await rig.interrogation_report_dao.get_by_id(file.id)
    assert stored_report.file_id == file.id
    assert stored_report.passed is False

    # Verify failure event was published
    failure_event = rig.event_store.get(rig.config.file_interrogations_topic)
    assert failure_event.payload["file_id"] == str(file.id)
    assert failure_event.payload["reason"] == "Checksum mismatch detected"


async def test_report_handling_ekss_error(rig: JointRig):
    """Test that a SecretsApiError from deposit_secret is wrapped in SecretDepositionError."""
    file = create_file_under_interrogation(HUB1)
    await rig.file_dao.insert(file)

    rig.secrets_client.deposit_secret.side_effect = SecretsClientPort.SecretsApiError()

    error_report = models.InterrogationReportWithSecret(
        file_id=file.id,
        storage_alias=file.storage_alias,
        bucket_id="interrogation1",
        object_id=uuid4(),
        interrogated_at=now_utc_ms_prec(),
        passed=True,
        secret=b"secret",
        encrypted_parts_md5=["abc"],
        encrypted_parts_sha256=["sha"],
        encrypted_size=1234,
    )

    with pytest.raises(rig.interrogation_handler.SecretDepositionError) as exc_info:
        await rig.interrogation_handler.handle_interrogation_report(report=error_report)

    assert str(file.id) in str(exc_info.value)

    # Verify the report was rolled back (not left in the DAO)
    with pytest.raises(ResourceNotFoundError):
        await rig.interrogation_report_dao.get_by_id(file.id)


async def test_process_file_upload_insertion(rig: JointRig):
    """Test the `.process_file_upload()` method to check the file insertion functionality"""
    file = create_file_under_interrogation(HUB1)
    file.state = "init"

    # This should get ignored because the state is 'init' (which is too soon)
    await rig.interrogation_handler.process_file_upload(file=file)

    # Prove that this file is not in the database
    with pytest.raises(ResourceNotFoundError):
        await rig.file_dao.get_by_id(file.id)

    # Run it again with the state set to 'inbox' and verify the file gets to the DB
    file.state = "inbox"
    await rig.interrogation_handler.process_file_upload(file=file)
    assert rig.file_dao.latest.model_dump() == file.model_dump()

    # Verify that running the method again doesn't raise an error
    await rig.interrogation_handler.process_file_upload(file=file)


async def test_process_file_upload_outdated(
    rig: JointRig, caplog: pytest.LogCaptureFixture
):
    """Test logic in `.process_file_upload()` that detects outdated events"""
    local_file = create_file_under_interrogation(HUB1)
    await rig.interrogation_handler.process_file_upload(file=local_file)

    outdated_file = local_file.model_copy()
    outdated_file.state = "archived"
    outdated_file.state_updated += timedelta(hours=-1)
    caplog.clear()
    caplog.set_level("INFO")
    await rig.interrogation_handler.process_file_upload(file=outdated_file)
    assert caplog.records[0].getMessage() == (
        f"Encountered old data for file {local_file.id}, ignoring."
    )

    # Make sure the local copy wasn't modified
    db_file = await rig.file_dao.get_by_id(local_file.id)
    assert db_file.state != outdated_file.state
    assert db_file.state == local_file.state
    assert db_file.state_updated != outdated_file.state_updated
    assert db_file.state_updated == local_file.state_updated


async def test_process_file_upload_updates(
    rig: JointRig, caplog: pytest.LogCaptureFixture
):
    """Test logic in `.process_file_upload()` that updates the local copy
    when the received FileUnderInterrogation (FileUpload) is newer.
    """
    local_file = create_file_under_interrogation(HUB1)
    local_file.interrogated = True  # Set interrogation status
    await rig.interrogation_handler.process_file_upload(file=local_file)

    # Verify file is in the database
    db_file = await rig.file_dao.get_by_id(local_file.id)
    assert db_file.state == local_file.state
    assert db_file.interrogated is True
    assert not db_file.can_remove

    # Create an updated version with a newer timestamp and "archived" state
    updated_file = db_file.model_copy()
    updated_file.state = "archived"
    updated_file.state_updated = now_utc_ms_prec() + timedelta(hours=1)
    updated_file.can_remove = False  # Start with False to verify it gets set to True

    caplog.clear()
    caplog.set_level("INFO")
    await rig.interrogation_handler.process_file_upload(file=updated_file)

    # Verify the file was updated in the database
    db_file_after = await rig.file_dao.get_by_id(local_file.id)
    assert db_file_after.state == "archived"
    assert db_file_after.can_remove is True
    assert db_file_after.interrogated is True  # Should be preserved
    assert db_file_after.state_updated == updated_file.state_updated

    # Check the log message
    assert any(
        f"File {local_file.id} arrived with state archived" in record.getMessage()
        for record in caplog.records
    )

    # Test with "failed" state as well
    failed_file = db_file_after.model_copy()
    failed_file.state = "failed"
    failed_file.state_updated = now_utc_ms_prec() + timedelta(hours=2)
    failed_file.can_remove = False

    caplog.clear()
    await rig.interrogation_handler.process_file_upload(file=failed_file)

    db_file_final = await rig.file_dao.get_by_id(local_file.id)
    assert db_file_final.state == "failed"
    assert db_file_final.can_remove is True
    assert db_file_final.interrogated is True

    # Verify log message for failed state
    assert any(
        f"File {local_file.id} arrived with state failed" in record.getMessage()
        for record in caplog.records
    )


async def test_get_files_not_yet_interrogated(rig: JointRig):
    """Test the `.get_files_not_yet_interrogated()` method"""
    # Assert that when there are no files, we still get an empty list
    assert (
        await rig.interrogation_handler.get_files_not_yet_interrogated(
            storage_alias=HUB1
        )
        == []
    )

    # Insert files for hub1 and hub 2
    hub1_files = [create_file_under_interrogation(HUB1) for _ in range(3)]
    hub2_files = [create_file_under_interrogation(HUB2) for _ in range(3)]
    for file in hub2_files + hub1_files:
        await rig.file_dao.insert(file)

    hub1_ids = set(f.id for f in hub1_files)
    hub2_ids = set(f.id for f in hub2_files)

    # Make sure the query mapping works by querying for one of the hubs
    retrieve_h1 = await rig.interrogation_handler.get_files_not_yet_interrogated(
        storage_alias=HUB1
    )
    assert set(f.id for f in retrieve_h1) == hub1_ids

    # Set a file to 'interrogated'
    hub1_files[0].interrogated = True
    hub1_files[0].can_remove = True
    hub1_files[0].state = "interrogated"
    await rig.file_dao.update(hub1_files[0])

    # Set another file to 'failed'
    hub2_files[0].state = "failed"
    hub2_files[0].interrogated = False
    hub2_files[0].can_remove = True
    await rig.file_dao.update(hub2_files[0])

    # Set another file to 'cancelled'
    hub2_files[1].state = "cancelled"
    hub2_files[1].interrogated = True
    hub2_files[1].can_remove = True
    await rig.file_dao.update(hub2_files[1])

    # Compare Hub 1 results
    hub1_ids.remove(hub1_files[0].id)
    results_h1 = await rig.interrogation_handler.get_files_not_yet_interrogated(
        storage_alias=HUB1
    )
    assert set(f.id for f in results_h1) == hub1_ids

    # Compare Hub 2 results
    hub2_ids.remove(hub2_files[0].id)
    hub2_ids.remove(hub2_files[1].id)
    results_h2 = await rig.interrogation_handler.get_files_not_yet_interrogated(
        storage_alias=HUB2
    )
    assert set(f.id for f in results_h2) == hub2_ids


async def test_ack_file_cancellation(rig: JointRig):
    """Test the `.ack_file_cancellation()` method"""
    # Test file not found error
    file = create_file_under_interrogation(HUB1)
    with pytest.raises(InterrogationHandlerPort.FileNotFoundError):
        await rig.interrogation_handler.ack_file_cancellation(file_id=file.id)

    # Insert a file
    file.state = "inbox"
    file.state_updated -= timedelta(hours=1)
    await rig.file_dao.insert(file)

    # Acknowledge the file cancellation
    await rig.interrogation_handler.ack_file_cancellation(file_id=file.id)

    # Verify file was updated
    updated_file = await rig.file_dao.get_by_id(file.id)
    assert updated_file.state == "cancelled"
    assert updated_file.can_remove is True
    assert updated_file.state_updated >= file.state_updated


async def test_report_handling_duplicate(rig: JointRig):
    """Test that submitting the same InterrogationReport twice is idempotent.

    The second submission should be silently ignored: no second event published,
    no second DB insert, and no error raised.
    """
    file = create_file_under_interrogation(HUB1)
    await rig.file_dao.insert(file)

    report = models.InterrogationReportWithSecret(
        file_id=file.id,
        storage_alias=file.storage_alias,
        bucket_id="interrogation1",
        object_id=uuid4(),
        interrogated_at=now_utc_ms_prec(),
        passed=True,
        secret=b"secret",
        encrypted_parts_md5=["abc"],
        encrypted_parts_sha256=["sha"],
        encrypted_size=100,
    )

    # First submission - processed normally
    await rig.interrogation_handler.handle_interrogation_report(report=report)
    stored = await rig.interrogation_report_dao.get_by_id(file.id)
    assert stored.passed is True

    # Second submission of the same report
    await rig.interrogation_handler.handle_interrogation_report(report=report)

    # deposit_secret should only have been called once (for the first submission)
    rig.secrets_client.deposit_secret.assert_called_once()

    # The stored report should be unchanged and there should still only be that one report
    stored_again = await rig.interrogation_report_dao.get_by_id(file.id)
    assert stored_again.passed is True

    # The file state should be the same
    db_file = await rig.file_dao.get_by_id(file.id)
    assert db_file.interrogated is True
    assert db_file.state == "interrogated"


async def test_report_handling_conflict(rig: JointRig):
    """Test that a second, contradicting InterrogationReport raises InterrogationReportConflict.

    If a report with different content is submitted for an already-interrogated file,
    the core should raise InterrogationReportConflict.
    """
    file = create_file_under_interrogation(HUB1)
    await rig.file_dao.insert(file)

    first_report = models.InterrogationReportWithSecret(
        file_id=file.id,
        storage_alias=file.storage_alias,
        bucket_id="interrogation1",
        object_id=uuid4(),
        interrogated_at=now_utc_ms_prec(),
        passed=True,
        secret=b"secret",
        encrypted_parts_md5=["abc"],
        encrypted_parts_sha256=["sha"],
        encrypted_size=100,
    )

    # First submission succeeds
    await rig.interrogation_handler.handle_interrogation_report(report=first_report)

    # Second report for the same file but with different content
    conflicting_report = models.InterrogationReportWithSecret(
        file_id=file.id,
        storage_alias=file.storage_alias,
        bucket_id=first_report.bucket_id,
        object_id=uuid4(),  # new object ID like what we'd see in a new interrogation
        interrogated_at=now_utc_ms_prec(),
        passed=True,
        secret=b"new-secret",  # in this scenario you'd also see a different secret
        encrypted_parts_md5=["abc"],
        encrypted_parts_sha256=["sha"],
        encrypted_size=100,
    )

    with pytest.raises(InterrogationHandlerPort.InterrogationReportConflict):
        await rig.interrogation_handler.handle_interrogation_report(
            report=conflicting_report
        )
