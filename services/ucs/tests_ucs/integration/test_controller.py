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

"""Integration tests for the UploadController"""

from contextlib import nullcontext
from tempfile import NamedTemporaryFile
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import pytest
from hexkit.correlation import set_correlation_id

from tests_ucs.fixtures import utils
from tests_ucs.fixtures.joint import JointFixture
from ucs.constants import FILE_UPLOADS_COLLECTION, S3_UPLOAD_DETAILS_COLLECTION
from ucs.core.models import FileUploadReport
from ucs.main import initialize
from ucs.ports.inbound.controller import UploadControllerPort

pytestmark = pytest.mark.asyncio()


async def test_integrated_aspects(joint_fixture: JointFixture):
    """Test aspects that are not easily testable with unit test mocks:
    - outbox event publishing (e.g. the result of `dto_to_event`)
    - validity of returned s3 file part upload URL

    This also serves as a truncated happy path test. It will not test all actions, just
    some of the core behavior branches.
    """
    wps_jwk = joint_fixture.wps_jwk
    uos_jwk = joint_fixture.uos_jwk
    kafka = joint_fixture.kafka
    config = joint_fixture.config
    rest_client = joint_fixture.rest_client

    async with nullcontext(NamedTemporaryFile("w+b")) as temp_file:
        # Create a box
        async with kafka.record_events(
            in_topic=config.file_upload_box_topic
        ) as box_recorder:
            token_header = utils.create_file_box_token_header(jwk=uos_jwk)
            box_creation_body = {"storage_alias": "test"}
            response = await rest_client.post(
                "/boxes", json=box_creation_body, headers=token_header
            )
            assert response.status_code == 201
            box_id = UUID(response.json())
        events = box_recorder.recorded_events
        assert events
        assert len(events) == 1
        assert events[0].type_ == "upserted"
        assert events[0].payload == {
            "id": str(box_id),
            "locked": False,
            "size": 0,
            "file_count": 0,
            "storage_alias": "test",
        }, "Payload was wrong for new file upload box event"

        # Make the temp test file
        file_size = 10 * 1024 * 1024  # 10 MiB
        chunk_size = 1024
        chunk = b"\0" * chunk_size
        current_size = 0
        while current_size < file_size:
            write_size = min(chunk_size, file_size - current_size)
            temp_file.write(chunk[:write_size])
            current_size += write_size
        temp_file.flush()

        # Create a FileUpload
        async with kafka.record_events(
            in_topic=config.file_upload_topic
        ) as file_recorder:
            create_file_token_header = utils.create_file_token_header(
                jwk=wps_jwk, box_id=box_id, alias="test_file"
            )
            file_creation_body = {
                "alias": "test_file",
                "checksum": "abc123",
                "size": file_size,
            }
            response = await rest_client.post(
                f"/boxes/{box_id}/uploads",
                json=file_creation_body,
                headers=create_file_token_header,
            )
            assert response.status_code == 201
            file_id = UUID(response.json())
        events = file_recorder.recorded_events
        assert events
        assert len(events) == 1
        assert events[0].type_ == "upserted"
        assert events[0].payload == {
            **file_creation_body,
            "state": "init",
            "completed": False,
            "id": str(file_id),
            "box_id": str(box_id),
        }, "Payload was wrong for new file upload event"

        # Get part upload URL for the file (should only require 1 part since file is under 16 MiB)
        upload_token_header = utils.upload_file_token_header(
            jwk=wps_jwk, box_id=box_id, file_id=file_id
        )
        response = await rest_client.get(
            f"/boxes/{box_id}/uploads/{file_id}/parts/1", headers=upload_token_header
        )
        url = str(response.json())

        # Actually upload dummy data to S3 fixture
        temp_file.seek(0)  # Reset file pointer to beginning

        # Use httpx directly instead of the test client to bypass routing
        response = httpx.put(url, content=temp_file.read(), timeout=30)
        assert response.status_code == 200

        # File is now uploaded, so complete the upload
        async with kafka.record_events(
            in_topic=config.file_upload_topic
        ) as file_recorder:
            close_file_token_header = utils.close_file_token_header(
                jwk=wps_jwk, box_id=box_id, file_id=file_id
            )
            response = await rest_client.patch(
                f"/boxes/{box_id}/uploads/{file_id}", headers=close_file_token_header
            )
        events = file_recorder.recorded_events
        assert len(events) == 1
        assert events[0].payload["state"] in ["inbox", "archived"]

        # Let's lock the box now and verify that it is reflected in the event
        async with kafka.record_events(
            in_topic=config.file_upload_box_topic
        ) as box_recorder:
            lock_box_token_header = utils.change_file_box_token_header(
                box_id=box_id, jwk=uos_jwk
            )
            box_update_body = {"lock": True}
            response = await rest_client.patch(
                f"/boxes/{box_id}", json=box_update_body, headers=lock_box_token_header
            )
            assert response.status_code == 204
        events = box_recorder.recorded_events
        assert len(events) == 1
        assert events[0].payload["locked"]

        # Now try to delete the file and verify that no event gets emitted
        async with kafka.record_events(
            in_topic=config.file_upload_topic
        ) as file_recorder:
            delete_file_token_header = utils.delete_file_token_header(
                jwk=wps_jwk, box_id=box_id, file_id=file_id
            )
            response = await rest_client.delete(
                f"/boxes/{box_id}/uploads/{file_id}", headers=delete_file_token_header
            )
            assert response.status_code == 409
        assert not file_recorder.recorded_events

        # Great, we verified that the locked box prevents changes. Now unlock the box
        #  but don't check for events -- satisfied at this point that outbox is working
        box_update_body = {"lock": False}
        unlock_box_token_header = utils.change_file_box_token_header(
            box_id=box_id, work_type="unlock", jwk=uos_jwk
        )
        response = await rest_client.patch(
            f"/boxes/{box_id}",
            json=box_update_body,
            headers=unlock_box_token_header,
        )
        assert response.status_code == 204

        # Delete the file finally
        response = await rest_client.delete(
            f"/boxes/{box_id}/uploads/{file_id}", headers=delete_file_token_header
        )
        assert response.status_code == 204


async def test_s3_upload_completed_but_db_not_updated(joint_fixture: JointFixture):
    """Test error handling when the S3 upload is successfully completed but a hard
    crash (simulated) causes the DB to never get updated.

    The FileUpload, S3UploadDetails, and FileUploadBox are not updated, even though
    the S3 operations were finished properly. In this case, the requester would not
    receive a meaningful error message and would have to retry the request. Upon issuing
    the request a second time, the UCS would see that the S3 upload has already been
    completed and would then update the DB documents accordingly.
    """
    controller = joint_fixture.upload_controller
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(storage_alias="test")
        file_id = await controller.initiate_file_upload(
            box_id=box_id, alias="test-file", checksum="abc123", size=1024
        )
    url = await controller.get_part_upload_url(file_id=file_id, part_no=1)

    # Upload the content
    response = httpx.put(url, content="a" * 1024)
    assert response.status_code == 200

    # To simulate the hiccup, we'll manually complete the upload. This will create the
    #  out-of-sync state described above.
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    s3_upload_details_collection = db[S3_UPLOAD_DETAILS_COLLECTION]
    uploads = s3_upload_details_collection.find().to_list()
    assert len(uploads) == 1
    assert not uploads[0]["completed"]
    upload_id = uploads[0]["s3_upload_id"]

    await joint_fixture.s3.storage.complete_multipart_upload(
        bucket_id="test-inbox", object_id=str(file_id), upload_id=upload_id
    )

    # Now call the completion endpoint using the rest client
    close_token_header = utils.close_file_token_header(
        box_id=box_id, file_id=file_id, jwk=joint_fixture.wps_jwk
    )
    response = await joint_fixture.rest_client.patch(
        f"/boxes/{box_id}/uploads/{file_id}", headers=close_token_header
    )

    # Response should indicate success because the file was uploaded
    assert response.status_code == 204

    # DB should now show that everything is complete
    uploads = s3_upload_details_collection.find().to_list()
    assert len(uploads) == 1
    assert uploads[0]["completed"]
    file_upload_collection = db[FILE_UPLOADS_COLLECTION]
    file_uploads = file_upload_collection.find(
        {"__metadata__.deleted": False}
    ).to_list()
    assert len(file_uploads) == 1
    assert file_uploads[0]["state"] in ["inbox", "archived"]
    assert uploads[0]["_id"] == file_uploads[0]["_id"]


async def test_s3_upload_complete_fails(joint_fixture: JointFixture):
    """Test error handling when the S3 upload completion command raises a
    MultiPartUploadConfirmError.

    In this case, the requester should receive an error indicating they need to
    delete the file upload and restart the process, since no recovery is possible.
    """
    wps_jwk = joint_fixture.wps_jwk
    rest_client = joint_fixture.rest_client
    controller = joint_fixture.upload_controller
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(storage_alias="test")
        file_id = await controller.initiate_file_upload(
            box_id=box_id, alias="test-file", checksum="abc123", size=1024
        )
    url = await controller.get_part_upload_url(file_id=file_id, part_no=1)

    # Upload the content
    response = httpx.put(url, content="a" * 1024)
    assert response.status_code == 200

    # To simulate the hiccup, we'll manually abort the upload. This will create the
    #  out-of-sync state described above.
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    s3_upload_details_collection = db[S3_UPLOAD_DETAILS_COLLECTION]
    uploads = s3_upload_details_collection.find().to_list()
    assert len(uploads) == 1
    assert not uploads[0]["completed"]
    upload_id = uploads[0]["s3_upload_id"]
    await joint_fixture.s3.storage.abort_multipart_upload(
        bucket_id="test-inbox", object_id=str(file_id), upload_id=upload_id
    )

    # Make the completion request with the rest client
    close_token_header = utils.close_file_token_header(
        box_id=box_id, file_id=file_id, jwk=wps_jwk
    )
    response = await rest_client.patch(
        f"/boxes/{box_id}/uploads/{file_id}", headers=close_token_header
    )
    # Response should indicate failure and parameters
    assert response.status_code == 500
    error = response.json()
    assert error["exception_id"] == "uploadCompletionError"
    assert error["data"] == {"box_id": str(box_id), "file_id": str(file_id)}

    # Now request deletion of the file
    delete_token_header = utils.delete_file_token_header(
        box_id=box_id, file_id=file_id, jwk=wps_jwk
    )
    response = await rest_client.delete(
        f"/boxes/{box_id}/uploads/{file_id}", headers=delete_token_header
    )
    assert response.status_code == 204

    # Now retry the upload process, obtaining a new file_id
    create_token_header = utils.create_file_token_header(
        box_id=box_id, alias="test-file", jwk=wps_jwk
    )
    body = {"alias": "test-file", "checksum": "abc123", "size": 1024}
    response = await rest_client.post(
        f"/boxes/{box_id}/uploads", headers=create_token_header, json=body
    )
    assert response.status_code == 201
    file_id2 = UUID(response.json())

    upload_token_header = utils.upload_file_token_header(
        box_id=box_id, file_id=file_id2, jwk=wps_jwk
    )
    response = await rest_client.get(
        f"/boxes/{box_id}/uploads/{file_id2}/parts/1", headers=upload_token_header
    )
    assert response.status_code == 200
    part_url = response.json()

    # Upload the content again
    response = httpx.put(part_url, content="a" * 1024)
    assert response.status_code == 200

    # Now complete the file
    close_token_header2 = utils.close_file_token_header(
        box_id=box_id, file_id=file_id2, jwk=wps_jwk
    )
    response = await rest_client.patch(
        f"/boxes/{box_id}/uploads/{file_id2}", headers=close_token_header2
    )
    assert response.status_code == 204

    # Check the DB to verify that docs were deleted for the old file upload and that
    #  the new file upload (for the same alias) exists instead, set to completed
    uploads = s3_upload_details_collection.find().to_list()
    assert len(uploads) == 1
    assert uploads[0]["_id"] == file_id2
    assert uploads[0]["completed"]
    file_upload_collection = db[FILE_UPLOADS_COLLECTION]
    file_uploads = file_upload_collection.find(
        {"__metadata__.deleted": False}
    ).to_list()
    assert len(file_uploads) == 1
    assert file_uploads[0]["state"] in ["inbox", "archived"]
    assert uploads[0]["_id"] == file_uploads[0]["_id"]


async def test_orphaned_s3_upload_in_file_create(joint_fixture: JointFixture, caplog):
    """A test for the scenario where a crash occurs in the `init_file_upload` method
    between creating the S3 upload and inserting the S3UploadDetails.

    The expected behavior is that the FileUpload is deleted, a critical error log
    is emitted, and the REST API returns a 409 CONFLICT error.
    """
    controller = joint_fixture.upload_controller
    s3_storage = joint_fixture.s3.storage
    bucket_id = joint_fixture.bucket_id

    # Create a box first
    correlation_id = uuid4()
    async with set_correlation_id(correlation_id):
        box_id = await controller.create_file_upload_box(storage_alias="test")

    # Simulate the scenario by manually creating an S3 upload first
    # This simulates the orphaned state where S3 has an upload but no DB record exists
    file_id = uuid4()
    s3_upload_id = await s3_storage.init_multipart_upload(
        bucket_id=bucket_id, object_id=str(file_id)
    )

    # Now try to create a file upload with the same file_id through the normal process
    # This should trigger the OrphanedMultipartUploadErrorError scenario
    # Patch the uuid4 generation to return the predetermined file_id
    create_token_header = utils.create_file_token_header(
        box_id=box_id, alias="test-file", jwk=joint_fixture.wps_jwk
    )
    body = {"alias": "test-file", "checksum": "abc123", "size": 1024}
    with (
        caplog.at_level("CRITICAL"),
        patch("ucs.core.controller.uuid4", return_value=file_id),
    ):
        caplog.clear()
        response = await joint_fixture.rest_client.post(
            f"/boxes/{box_id}/uploads", headers=create_token_header, json=body
        )
    assert response.status_code == 409
    http_error = response.json()
    assert http_error["exception_id"] == "orphanedMultipartUpload"

    # Verify that the FileUpload was cleaned up (deleted from DB)
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    file_upload_collection = db[FILE_UPLOADS_COLLECTION]
    file_uploads = file_upload_collection.find(
        {"__metadata__.deleted": False, "_id": file_id}
    ).to_list()
    assert len(file_uploads) == 0, "FileUpload should have been deleted during cleanup"

    records = caplog.records
    assert len(records) == 1
    expected_log_msg = (
        f"An S3 multipart upload already exists for file ID {file_id}"
        + f" and bucket ID {bucket_id}."
    )
    assert records[0].msg == expected_log_msg

    # Verify that no S3UploadDetails were created
    s3_upload_details_collection = db[S3_UPLOAD_DETAILS_COLLECTION]
    s3_uploads = s3_upload_details_collection.find({"_id": file_id}).to_list()
    assert len(s3_uploads) == 0, "No S3UploadDetails should exist for the failed upload"

    # Clean up the orphaned S3 upload for this test
    await s3_storage.abort_multipart_upload(
        bucket_id=bucket_id, object_id=str(file_id), upload_id=s3_upload_id
    )


async def test_file_upload_index(joint_fixture: JointFixture, monkeypatch):
    """Test that the compound FileUpload index works"""
    monkeypatch.setattr("ucs.main.Config", lambda: joint_fixture.config)

    async with set_correlation_id(uuid4()):
        await initialize()

        box_id = await joint_fixture.upload_controller.create_file_upload_box(
            storage_alias="test"
        )
        _ = await joint_fixture.upload_controller.initiate_file_upload(
            box_id=box_id, alias="file1", checksum="blah", size=1024
        )
        with pytest.raises(UploadControllerPort.FileUploadAlreadyExists):
            _ = await joint_fixture.upload_controller.initiate_file_upload(
                box_id=box_id, alias="file1", checksum="blah", size=1024
            )


async def test_file_upload_report_happy(joint_fixture: JointFixture):
    """Test the normal path of receiving a FileUploadReport event and deleting the file
    from the S3 bucket.
    """
    controller = joint_fixture.upload_controller
    s3_storage = joint_fixture.s3.storage
    bucket_id = joint_fixture.bucket_id
    config = joint_fixture.config

    # Create a box and initiate a file upload
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(storage_alias="test")
        file_id = await controller.initiate_file_upload(
            box_id=box_id, alias="test-file", checksum="abc123", size=1024
        )

    # Get upload URL and upload the file content
    url = await controller.get_part_upload_url(file_id=file_id, part_no=1)
    response = httpx.put(url, content="a" * 1024)
    assert response.status_code == 200

    # Complete the file upload
    async with set_correlation_id(uuid4()):
        await controller.complete_file_upload(box_id=box_id, file_id=file_id)

    # Verify the file exists in S3
    object_id = str(file_id)
    file_exists_before = await s3_storage.does_object_exist(
        bucket_id=bucket_id, object_id=object_id
    )
    assert file_exists_before

    # Verify the database records exist
    db = joint_fixture.mongodb.client[config.db_name]
    s3_upload_details_collection = db[S3_UPLOAD_DETAILS_COLLECTION]
    file_upload_collection = db[FILE_UPLOADS_COLLECTION]

    s3_uploads_before = s3_upload_details_collection.find({"_id": file_id}).to_list()
    assert len(s3_uploads_before) == 1
    assert s3_uploads_before[0]["completed"]

    file_uploads_before = file_upload_collection.find(
        {"_id": file_id, "__metadata__.deleted": False}
    ).to_list()
    assert len(file_uploads_before) == 1
    assert file_uploads_before[0]["state"] == "inbox"

    # Create and publish a FileUploadReport event
    file_upload_report = FileUploadReport(
        file_id=file_id, secret_id="test-secret-123", passed_inspection=True
    )

    await joint_fixture.kafka.publish_event(
        payload=file_upload_report.model_dump(),
        type_=config.file_upload_reports_type,
        topic=config.file_upload_reports_topic,
    )

    # Consume the event
    await joint_fixture.event_subscriber.run(forever=False)

    # Verify the file has been deleted from S3
    file_exists_after = await s3_storage.does_object_exist(
        bucket_id=bucket_id, object_id=object_id
    )
    assert not file_exists_after

    # Verify the FileUpload state was updated
    file_uploads_after = file_upload_collection.find().to_list()
    assert len(file_uploads_after) == 1
    assert file_uploads_after[0]["state"] == "archived"

    # Now test for idempotency by repeating the publish and consume
    await joint_fixture.kafka.publish_event(
        payload=file_upload_report.model_dump(),
        type_=config.file_upload_reports_type,
        topic=config.file_upload_reports_topic,
    )

    # Consume the event -- should not receive an error
    await joint_fixture.event_subscriber.run(forever=False)
