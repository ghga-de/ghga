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

"""Integration tests for the Interrogator class"""

import asyncio
import json
import time
from typing import cast
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx2
import pytest
from pydantic import SecretBytes

from dhfs.adapters.outbound.s3 import S3Client
from dhfs.core.interrogator import Interrogator
from dhfs.core.models import FileUpload
from tests.fixtures.central_api import capture, fail_to_connect, respond
from tests.fixtures.joint import JointFixture
from tests.fixtures.utils import (
    EncryptedObject,
    get_encrypted_object,
    upload_encrypted_object,
)

PART_SIZE = 6 * (1024**2)  # 6291456 bytes
INBOX = "inbox1"


pytestmark = pytest.mark.asyncio


async def test_interrogate_new_files(joint_fixture: JointFixture, caplog):
    """Test the interrogation process for a single file"""
    # Create the inbox bucket
    config = joint_fixture.config
    await joint_fixture.s3.storage.create_bucket(INBOX)

    # Add files to the inbox
    object_ids = sorted([str(uuid4()) for _ in range(2)])
    file_uploads: list[FileUpload] = []
    for object_id in object_ids:
        encrypted_object = get_encrypted_object(
            part_size=PART_SIZE, file_size=int(PART_SIZE * 2.5)
        )
        await upload_encrypted_object(
            bucket_id=INBOX,
            object_id=object_id,
            storage=joint_fixture.s3.storage,
            encrypted_object=encrypted_object,
        )
        file_uploads.append(
            FileUpload(
                id=uuid4(),
                decrypted_sha256=encrypted_object.checksums.unencrypted_sha256.hexdigest(),
                storage_alias=config.storage_alias,
                bucket_id=INBOX,
                object_id=UUID(object_id),
                decrypted_size=encrypted_object.unencrypted_size,
                encrypted_size=encrypted_object.encrypted_size,
                part_size=PART_SIZE,
            )
        )

    # Create the interrogation bucket so the re-encrypted files have a place to go
    interrogation = joint_fixture.config.interrogation_bucket_id
    await joint_fixture.s3.storage.create_bucket(interrogation)

    # Serialize the file uploads we prepared in advance to JSON
    serialized_file_uploads = [x.model_dump(mode="json") for x in file_uploads]

    # Mock the endpoint that returns the list of new files that need interrogation
    joint_fixture.central_api.on_fetch_new_uploads = respond(
        200, json=serialized_file_uploads
    )

    # Mock the endpoint we upload the file interrogation report to, tracking reports
    received_reports = []
    joint_fixture.central_api.on_submit_report = capture(received_reports)

    # Process all files
    with caplog.at_level("INFO"):
        await joint_fixture.interrogator.interrogate_new_files()

    # Check the interrogation bucket
    s3_client: S3Client = joint_fixture.interrogator._s3_client  # type: ignore
    interrogation_files = set(await s3_client.list_files_in_interrogation_bucket())

    assert interrogation_files.isdisjoint(object_ids)
    assert interrogation_files.isdisjoint(f.id for f in file_uploads)

    # Verify that we received reports for all files
    assert len(received_reports) == 2, (
        f"Expected 2 reports, got {len(received_reports)}"
    )

    # Files are processed one at a time, in the order the batch listed them, so the
    #  reports arrive in that order too.
    assert [report["file_id"] for report in received_reports] == [
        str(f.id) for f in file_uploads
    ]
    reports_by_file_id = {report["file_id"]: report for report in received_reports}

    # Verify each report has the correct structure for successful interrogation
    for file_upload in file_uploads:
        report = reports_by_file_id[str(file_upload.id)]
        assert report["storage_alias"] == file_upload.storage_alias
        assert report["bucket_id"] == config.interrogation_bucket_id
        assert report["passed"] is True
        assert report["reason"] is None
        assert report["interrogated_at"] is not None
        assert report["secret"] is not None
        assert isinstance(report["encrypted_parts_md5"], list)
        assert len(report["encrypted_parts_md5"]) > 0
        assert isinstance(report["encrypted_parts_sha256"], list)
        assert len(report["encrypted_parts_sha256"]) > 0

    # Verify the per-file phase-timing log was emitted for each file
    phase_timing_logs = [
        record
        for record in caplog.records
        if "Re-encryption process complete" in record.message
    ]
    assert len(phase_timing_logs) == len(file_uploads), (
        "Expected one phase-timing log per file"
    )
    expected_float_fields = (
        "download_s",
        "decrypt_s",
        "reencrypt_s",
        "verify_s",
        "upload_s",
        "total_s",
    )
    for log_record in phase_timing_logs:
        for field in expected_float_fields:
            assert hasattr(log_record, field), f"Missing structured field: {field}"
            assert isinstance(getattr(log_record, field), float)
    expected_int_fields = (
        "download_mib_per_s",
        "decrypt_mib_per_s",
        "reencrypt_mib_per_s",
        "verify_mib_per_s",
        "upload_mib_per_s",
        "total_mib_per_s",
    )
    for log_record in phase_timing_logs:
        for field in expected_int_fields:
            assert hasattr(log_record, field), f"Missing structured field: {field}"
            assert isinstance(getattr(log_record, field), int)


async def test_report_failure(joint_fixture: JointFixture):
    """Test the content sent by .report_failure()"""
    config = joint_fixture.config

    # Generate a test file ID and failure reason
    file_id = uuid4()
    failure_reason = "Test failure: File decryption failed"

    # Track the payload received by the handler
    received_payload = None

    def capture_payload(request: httpx2.Request) -> httpx2.Response:
        """Handler to capture the payload sent to the API"""
        nonlocal received_payload
        received_payload = request.content.decode("utf-8")
        return httpx2.Response(status_code=201, json={})

    # Mock the interrogation report submission endpoint with the handler
    joint_fixture.central_api.on_submit_report = capture_payload

    # Call report_failure
    await joint_fixture.interrogator.report_failure(
        file_id=file_id, reason=failure_reason
    )

    # Verify the payload was received
    assert received_payload is not None, "No payload was received"

    # Parse the JSON payload
    payload = json.loads(received_payload)

    # Verify the payload structure and content
    assert payload["file_id"] == str(file_id)
    assert payload["storage_alias"] == config.storage_alias
    assert payload["passed"] is False
    assert payload["reason"] == failure_reason
    assert payload["interrogated_at"] is not None
    assert payload["secret"] is None
    assert payload["encrypted_parts_md5"] is None
    assert payload["encrypted_parts_sha256"] is None


async def test_api_down_during_report_submission(
    joint_fixture: JointFixture, monkeypatch
):
    """Test that a failed report submission does not raise and leaves the
    re-encrypted file in the interrogation bucket so it is not re-processed
    with a different secret on the next invocation.
    """
    # Create the inbox bucket
    config = joint_fixture.config
    await joint_fixture.s3.storage.create_bucket(INBOX)

    # Add a file to the inbox
    object_id = str(uuid4())
    encrypted_object = get_encrypted_object(
        part_size=PART_SIZE, file_size=int(PART_SIZE * 2.5)
    )
    await upload_encrypted_object(
        bucket_id=INBOX,
        object_id=object_id,
        storage=joint_fixture.s3.storage,
        encrypted_object=encrypted_object,
    )
    file_upload = FileUpload(
        id=uuid4(),
        decrypted_sha256=encrypted_object.checksums.unencrypted_sha256.hexdigest(),
        storage_alias=config.storage_alias,
        bucket_id=INBOX,
        object_id=UUID(object_id),
        decrypted_size=encrypted_object.unencrypted_size,
        encrypted_size=encrypted_object.encrypted_size,
        part_size=PART_SIZE,
    )

    # Create the interrogation bucket
    interrogation = config.interrogation_bucket_id
    await joint_fixture.s3.storage.create_bucket(interrogation)

    # Mock the endpoint that returns new files to interrogate
    joint_fixture.central_api.on_fetch_new_uploads = respond(
        200, json=[file_upload.model_dump(mode="json")]
    )

    # Mock the report submission endpoint to fail (simulating API down)
    joint_fixture.central_api.on_submit_report = respond(503)

    # Generate a known value for the reencrypted object ID so we can check it later
    interrogation_object_id = uuid4()

    # Monkeypatch the uuid4 function so it produces the above ID
    monkeypatch.setattr("dhfs.core.interrogator.uuid4", lambda: interrogation_object_id)

    # Processing should complete without raising despite the failed submission
    await joint_fixture.interrogator.interrogate_new_files()

    # Verify the re-encrypted file is still in the interrogation bucket
    s3_client: S3Client = joint_fixture.interrogator._s3_client  # type: ignore
    interrogation_files = await s3_client.list_files_in_interrogation_bucket()

    assert interrogation_files == [str(interrogation_object_id)], (
        "Re-encrypted file should remain in the interrogation bucket after a"
        " failed report submission"
    )


async def test_file_not_in_inbox(joint_fixture: JointFixture, caplog):
    """Make sure we abort the interrogation without reporting failure if an
    expected file isn't found in the inbox.
    """
    # Create the inbox bucket
    config = joint_fixture.config
    await joint_fixture.s3.storage.create_bucket(INBOX)

    file_upload = FileUpload(
        id=uuid4(),
        decrypted_sha256="abc123",
        storage_alias=config.storage_alias,
        bucket_id=INBOX,
        object_id=uuid4(),
        decrypted_size=1024,
        encrypted_size=1228,
        part_size=PART_SIZE,
    )

    # Mock the endpoint that returns new files to interrogate
    joint_fixture.central_api.on_fetch_new_uploads = respond(
        200, json=[file_upload.model_dump(mode="json")]
    )

    # Try to interrogate - will get a log about it but no error (so dhfs can continue)
    err_msg = (
        f"File {file_upload.id}: Unable to conclusively process file - will retry"
        + f" later. Reason: The file {file_upload.id}, under object ID"
        + f" {file_upload.object_id} was not found in the inbox"
    )
    with caplog.at_level("WARNING"):
        caplog.clear()
        await joint_fixture.interrogator.interrogate_new_files()
    assert err_msg in caplog.text


async def test_file_decryption_error(joint_fixture: JointFixture):
    """Make sure that after a decryption problem we stop interrogation, abort the
    active upload, and report failure to the central API.
    """
    # Create the inbox bucket
    config = joint_fixture.config
    await joint_fixture.s3.storage.create_bucket(INBOX)

    # Create an encrypted object but corrupt its content to cause decryption failure
    object_id = str(uuid4())
    encrypted_object = get_encrypted_object(
        part_size=PART_SIZE, file_size=int(PART_SIZE * 2.5)
    )

    # Corrupt the encrypted content (but keep the envelope intact)
    corrupted_data = bytearray(encrypted_object.data)
    # Corrupt some bytes in the encrypted content after the envelope
    corruption_start = encrypted_object.offset + 100
    for i in range(corruption_start, corruption_start + 50):
        corrupted_data[i] = (corrupted_data[i] + 1) % 256

    # Create a corrupted EncryptedObject with the same metadata but corrupted data
    corrupted_object = EncryptedObject(
        checksums=encrypted_object.checksums,
        unencrypted_size=encrypted_object.unencrypted_size,
        encrypted_size=encrypted_object.encrypted_size,
        part_size=encrypted_object.part_size,
        offset=encrypted_object.offset,
        data=bytes(corrupted_data),
    )

    # Upload the object
    await upload_encrypted_object(
        bucket_id=INBOX,
        object_id=object_id,
        storage=joint_fixture.s3.storage,
        encrypted_object=corrupted_object,
    )

    file_upload = FileUpload(
        id=uuid4(),
        decrypted_sha256=encrypted_object.checksums.unencrypted_sha256.hexdigest(),
        storage_alias=config.storage_alias,
        bucket_id=INBOX,
        object_id=UUID(object_id),
        decrypted_size=encrypted_object.unencrypted_size,
        encrypted_size=encrypted_object.encrypted_size,
        part_size=PART_SIZE,
    )

    # Create the interrogation bucket
    interrogation = config.interrogation_bucket_id
    await joint_fixture.s3.storage.create_bucket(interrogation)

    # Mock the endpoint that returns new files to interrogate
    joint_fixture.central_api.on_fetch_new_uploads = respond(
        200, json=[file_upload.model_dump(mode="json")]
    )

    # Mock the report submission endpoint, tracking the failure reports received
    received_reports = []
    joint_fixture.central_api.on_submit_report = capture(received_reports)

    # Process files - should handle the decryption error gracefully
    await joint_fixture.interrogator.interrogate_new_files()

    # Verify that a failure report was submitted
    assert len(received_reports) == 1, "Expected one failure report"
    report = received_reports[0]
    assert report["passed"] is False, "Report should indicate failure"
    assert report["file_id"] == str(file_upload.id)

    # The important thing is that passed=False and a report was submitted
    assert report["reason"] is not None, "Reason field should exist"

    # Verify that the interrogation bucket is empty (upload was aborted/cleaned up)
    s3_client: S3Client = joint_fixture.interrogator._s3_client  # type: ignore
    interrogation_files = await s3_client.list_files_in_interrogation_bucket()
    assert interrogation_files == [], (
        "Interrogation bucket should be empty after decryption failure"
    )


async def test_etag_doesnt_match_local_md5(
    joint_fixture: JointFixture, monkeypatch, caplog
):
    """Make sure that an ETag mismatch is treated as an inconclusive error.

    A mismatch here most likely indicates a problem on our end (the file passed
    checks in the Upload Controller Service), so we do NOT report failure to the
    Central API. Instead we log a warning, clean up the re-encrypted object, and
    let the file be retried on the next invocation.
    """
    # Create the inbox bucket
    config = joint_fixture.config
    await joint_fixture.s3.storage.create_bucket(INBOX)

    # Add a file to the inbox
    object_id = str(uuid4())
    encrypted_object = get_encrypted_object(
        part_size=PART_SIZE, file_size=int(PART_SIZE * 2.5)
    )
    await upload_encrypted_object(
        bucket_id=INBOX,
        object_id=object_id,
        storage=joint_fixture.s3.storage,
        encrypted_object=encrypted_object,
    )
    file_upload = FileUpload(
        id=uuid4(),
        decrypted_sha256=encrypted_object.checksums.unencrypted_sha256.hexdigest(),
        storage_alias=config.storage_alias,
        bucket_id=INBOX,
        object_id=UUID(object_id),
        decrypted_size=encrypted_object.unencrypted_size,
        encrypted_size=encrypted_object.encrypted_size,
        part_size=PART_SIZE,
    )

    # Create the interrogation bucket
    interrogation = config.interrogation_bucket_id
    await joint_fixture.s3.storage.create_bucket(interrogation)

    # Mock the endpoint that returns new files to interrogate
    joint_fixture.central_api.on_fetch_new_uploads = respond(
        200, json=[file_upload.model_dump(mode="json")]
    )

    # Guard: if any report is submitted, the test should fail immediately
    def report_should_not_be_called(request: httpx2.Request) -> httpx2.Response:
        raise RuntimeError("No interrogation report should have been submitted!")

    joint_fixture.central_api.on_submit_report = report_should_not_be_called

    # Patch complete_upload to return a wrong ETag, simulating an S3 integrity mismatch
    s3_client: S3Client = joint_fixture.interrogator._s3_client  # type: ignore
    original_complete = s3_client.complete_upload

    async def complete_with_wrong_etag(
        upload_id: str, object_id: str, part_count: int
    ) -> str:
        await original_complete(
            upload_id=upload_id, object_id=object_id, part_count=part_count
        )
        return "wrong-etag-12345-99"

    monkeypatch.setattr(s3_client, "complete_upload", complete_with_wrong_etag)

    with caplog.at_level("INFO"):
        await joint_fixture.interrogator.interrogate_new_files()

    # Verify the ETag mismatch warning was logged
    assert (
        "The S3 ETag (MD5 checksum) doesn't match the locally calculated value."
        in caplog.text
    )

    # Verify the file was cleaned up from the interrogation bucket
    assert "Removed object from the" in caplog.text
    assert "bucket - cleanup complete." in caplog.text

    # Verify the inconclusive-retry warning was logged (no report sent, retry later)
    assert "Unable to conclusively process file - will retry later." in caplog.text
    assert "Encrypted content checksum did not match the expected value." in caplog.text

    # Verify the interrogation bucket is empty after cleanup
    interrogation_files = await s3_client.list_files_in_interrogation_bucket()
    assert interrogation_files == [], (
        "Interrogation bucket should be empty after ETag mismatch cleanup"
    )


@pytest.mark.parametrize("status_code", [400, 404, 409, 500])
async def test_central_api_error_on_fetch_new_files(
    joint_fixture: JointFixture,
    status_code: int,
    caplog,
):
    """Test that a non-200 response from fetch_new_uploads is logged explicitly."""
    joint_fixture.central_api.on_fetch_new_uploads = respond(status_code)

    with caplog.at_level("ERROR"):
        await joint_fixture.interrogator.interrogate_new_files()

    assert "The GHGA Central API returned an error response" in caplog.text


async def test_central_api_bad_format_on_fetch_new_files(
    joint_fixture: JointFixture,
    caplog,
):
    """Test that an unparseable response from fetch_new_uploads is logged explicitly."""
    joint_fixture.central_api.on_fetch_new_uploads = respond(
        200, json={"not": "a list of file uploads"}
    )

    with caplog.at_level("ERROR"):
        await joint_fixture.interrogator.interrogate_new_files()

    assert (
        "The GHGA Central API returned an unrecognized response format" in caplog.text
    )


@pytest.mark.parametrize("status_code", [400, 404, 409, 500])
async def test_central_api_error_on_report_success(
    joint_fixture: JointFixture,
    status_code: int,
    caplog,
):
    """Test that a non-201 response from submit_interrogation_report in
    report_success() is logged explicitly without raising.
    """
    config = joint_fixture.config
    joint_fixture.central_api.on_submit_report = respond(status_code)

    with caplog.at_level("ERROR"):
        await joint_fixture.interrogator.report_success(
            file_id=uuid4(),
            bucket_id=config.interrogation_bucket_id,
            object_id=uuid4(),
            secret=SecretBytes(b"\x00" * 32),
            encrypted_parts_md5=[],
            encrypted_parts_sha256=[],
            encrypted_size=0,
        )

    assert (
        "The GHGA Central API returned an error response while submitting the file processing report"
        in caplog.text
    )


@pytest.mark.parametrize("status_code", [400, 404, 409, 500])
async def test_central_api_error_on_report_failure(
    joint_fixture: JointFixture,
    status_code: int,
    caplog,
):
    """Test that a non-201 response from submit_interrogation_report in
    report_failure is logged explicitly without raising.
    """
    joint_fixture.central_api.on_submit_report = respond(status_code)

    with caplog.at_level("ERROR"):
        await joint_fixture.interrogator.report_failure(
            file_id=uuid4(), reason="test failure"
        )

    assert (
        "The GHGA Central API returned an error response while submitting the file processing report"
        in caplog.text
    )


async def test_connection_failed_on_report_failure(
    joint_fixture: JointFixture,
    caplog,
):
    """Test that a connection failure during report_failure is logged explicitly
    without raising.
    """
    joint_fixture.central_api.on_submit_report = fail_to_connect()

    with caplog.at_level("ERROR"):
        await joint_fixture.interrogator.report_failure(
            file_id=uuid4(), reason="test failure"
        )

    assert (
        "Unable to reach the GHGA Central API while submitting the file processing report"
        in caplog.text
    )


async def _stage_batch(
    joint_fixture: JointFixture, count: int, file_size: int = int(PART_SIZE * 3.5)
) -> list[FileUpload]:
    """Put `count` multipart files in the inbox and announce them to the interrogator."""
    config = joint_fixture.config
    await joint_fixture.s3.storage.create_bucket(INBOX)
    await joint_fixture.s3.storage.create_bucket(config.interrogation_bucket_id)

    file_uploads: list[FileUpload] = []
    for _ in range(count):
        object_id = str(uuid4())
        encrypted_object = get_encrypted_object(
            part_size=PART_SIZE, file_size=file_size
        )
        await upload_encrypted_object(
            bucket_id=INBOX,
            object_id=object_id,
            storage=joint_fixture.s3.storage,
            encrypted_object=encrypted_object,
        )
        file_uploads.append(
            FileUpload(
                id=uuid4(),
                decrypted_sha256=encrypted_object.checksums.unencrypted_sha256.hexdigest(),
                storage_alias=config.storage_alias,
                bucket_id=INBOX,
                object_id=UUID(object_id),
                decrypted_size=encrypted_object.unencrypted_size,
                encrypted_size=encrypted_object.encrypted_size,
                part_size=PART_SIZE,
            )
        )

    joint_fixture.central_api.on_fetch_new_uploads = respond(
        200, json=[f.model_dump(mode="json") for f in file_uploads]
    )
    joint_fixture.central_api.on_submit_report = respond(201, json={})
    return file_uploads


async def test_files_are_processed_one_at_a_time(joint_fixture: JointFixture):
    """A batch is worked through in sequence, never two files at once.

    Parts are the only thing processed concurrently, which is what keeps peak memory a
    function of `max_concurrent_parts` alone rather than of it times a file count.
    """
    await _stage_batch(joint_fixture, count=2)

    interrogator = cast(Interrogator, joint_fixture.interrogator)
    original_interrogate_file = interrogator.interrogate_file
    windows: list[tuple[float, float]] = []

    async def timed_interrogate_file(file_upload: FileUpload) -> None:
        started = time.monotonic()
        try:
            await original_interrogate_file(file_upload)
        finally:
            windows.append((started, time.monotonic()))

    with patch.object(interrogator, "interrogate_file", timed_interrogate_file):
        await interrogator.interrogate_new_files()

    assert len(windows) == 2
    windows.sort()
    assert windows[0][1] <= windows[1][0], (
        f"Files overlapped: {windows[0]} and {windows[1]}"
    )


async def test_part_concurrency_is_bounded(joint_fixture: JointFixture):
    """`max_concurrent_parts` caps how many parts of a file are in flight at once."""
    await _stage_batch(joint_fixture, count=1)

    budget = 2
    interrogator = cast(Interrogator, joint_fixture.interrogator)
    interrogator._max_concurrent_parts = budget

    in_flight = 0
    peak = 0
    original_prepare = interrogator._prepare_part

    async def counting_prepare(ctx, **kwargs):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        try:
            return await original_prepare(ctx, **kwargs)
        finally:
            in_flight -= 1

    with patch.object(interrogator, "_prepare_part", counting_prepare):
        await interrogator.interrogate_new_files()

    # The file has several parts, so the budget has to actually bind
    assert peak > 1, "test did not exercise any concurrency"
    assert peak <= budget, (
        f"{peak} parts were in flight at once, above the budget of {budget}"
    )


async def test_parts_completing_out_of_order(joint_fixture: JointFixture):
    """Both integrity checks that conclude interrogation are order-sensitive: the
    whole-file SHA-256 over the decrypted content, and the ETag derived from the
    concatenated per-part MD5s. Completing them with the part order deliberately
    inverted is what proves the reordering logic holds.
    """
    # Enough parts that concurrency and the hand-off between them actually matter
    [file_upload] = await _stage_batch(
        joint_fixture, count=1, file_size=int(PART_SIZE * 5.5)
    )
    expected_part_count = len(list(file_upload.calc_encrypted_part_ranges()))
    assert expected_part_count > 1, "test needs a multipart file to be meaningful"

    received_reports = []
    joint_fixture.central_api.on_submit_report = capture(received_reports)

    # Delay earlier parts the most, so downloads finish in reverse order
    interrogator = cast(Interrogator, joint_fixture.interrogator)
    original_download = interrogator._download_part

    async def staggered_download(ctx):
        await asyncio.sleep(0.05 * (expected_part_count - ctx.part_no))
        return await original_download(ctx)

    with patch.object(interrogator, "_download_part", staggered_download):
        await interrogator.interrogate_file(file_upload)

    assert len(received_reports) == 1
    report = received_reports[0]
    assert report["passed"] is True
    assert len(report["encrypted_parts_md5"]) == expected_part_count
    assert len(report["encrypted_parts_sha256"]) == expected_part_count
