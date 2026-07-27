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

"""Integration tests for the UploadController"""

import hashlib
from contextlib import asynccontextmanager, nullcontext
from datetime import timedelta
from tempfile import NamedTemporaryFile
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import pytest
from ghga_event_schemas.pydantic_ import FileDeletionRequested, InterrogationSuccess
from hexkit.correlation import set_correlation_id
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.utils import now_utc_ms_prec

from tests_ucs.fixtures import utils
from tests_ucs.fixtures.joint import JointFixture
from ucs.adapters.outbound.dao import FIELDS_NOT_PUBLISHED
from ucs.constants import FILE_UPLOADS_COLLECTION, UPLOAD_ACTIVITY_COLLECTION
from ucs.main import perform_cleanup
from ucs.ports.inbound.controller import UploadControllerPort

pytestmark = pytest.mark.asyncio()
CONTENT = "a" * 10 * 1024 * 1024  # 10 MiB
ENCRYPTED_SIZE = len(CONTENT)
DECRYPTED_SIZE = ENCRYPTED_SIZE - 124


def calc_expected_encrypted_checksum(content: str) -> str:
    """Calculate the expected checksum for 'encrypted' (test) data in S3.

    This assumes only one object part for simplicity.
    """
    part_md5 = hashlib.md5(content.encode(), usedforsecurity=False).digest()
    object_md5 = hashlib.md5(part_md5, usedforsecurity=False).hexdigest()
    return object_md5 + "-1"  # only one part


async def upload_to_s3(url: str, content: str | bytes) -> httpx.Response:
    """Upload content to a pre-signed S3 URL.

    Uses httpx directly instead of the test client in order to bypass routing.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        return await client.put(url, content=content)


async def test_integrated_aspects(joint_fixture: JointFixture):
    """Test aspects that are not easily testable with unit test mocks:
    - outbox event publishing (e.g. the result of `dto_to_event`)
    - validity of returned s3 file part upload URL

    This also serves as a truncated happy path test. It will not test all actions, just
    some of the core behavior branches.
    """
    wps_jwk = joint_fixture.wps_jwk
    rs_jwk = joint_fixture.rs_jwk
    kafka = joint_fixture.kafka
    config = joint_fixture.config
    rest_client = joint_fixture.rest_client

    async with nullcontext(NamedTemporaryFile("w+b")) as temp_file:
        # Create a box
        async with kafka.record_events(
            in_topic=config.file_upload_box_topic
        ) as box_recorder:
            token_header = utils.create_file_box_token_header(jwk=rs_jwk)
            box_creation_body = {
                "storage_alias": "test",
                "max_size": utils.TEST_MAX_BOX_SIZE,
            }
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
            "version": 0,
            "state": "open",
            "size": 0,
            "max_size": utils.TEST_MAX_BOX_SIZE,
            "file_count": 0,
            "storage_alias": "test",
        }, "Payload was wrong for new file upload box event"

        # Make the temp test file
        temp_file.write(CONTENT.encode())
        temp_file.flush()

        expected_encrypted_checksum = calc_expected_encrypted_checksum(CONTENT)

        # Create a FileUpload
        async with kafka.record_events(
            in_topic=config.file_upload_topic
        ) as file_recorder:
            create_file_token_header = utils.create_file_token_header(
                jwk=wps_jwk, box_id=box_id, alias="test_file"
            )
            file_creation_body = {
                "alias": "test_file",
                "decrypted_size": DECRYPTED_SIZE,
                "encrypted_size": ENCRYPTED_SIZE,
                "part_size": utils.PART_SIZE,
            }
            response = await rest_client.post(
                f"/boxes/{box_id}/uploads",
                json=file_creation_body,
                headers=create_file_token_header,
            )
            assert response.status_code == 201
            file_creation_response_body = response.json()
            assert "file_id" in file_creation_response_body
            assert "alias" in file_creation_response_body
            assert "storage_alias" in file_creation_response_body
            file_id = UUID(file_creation_response_body["file_id"])
            assert "storage_alias" != ""
            assert file_creation_response_body["alias"] == file_creation_body["alias"]

        events = file_recorder.recorded_events
        assert events
        assert len(events) == 1
        assert events[0].type_ == "upserted"
        assert events[0].payload["state"] == "init"
        assert events[0].payload["id"] == str(file_id)
        assert events[0].payload["box_id"] == str(box_id)

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

        response = await upload_to_s3(url, temp_file.read())
        assert response.status_code == 200

        # File is now uploaded, so complete the upload
        # After this, _update_box_stats increments box version from 0 → 1
        async with kafka.record_events(
            in_topic=config.file_upload_topic
        ) as file_recorder:
            close_file_token_header = utils.close_file_token_header(
                jwk=wps_jwk, box_id=box_id, file_id=file_id
            )
            body = {
                "decrypted_sha256": "abc123",
                "encrypted_md5": expected_encrypted_checksum,
                "encrypted_parts_md5": ["abc123"],
                "encrypted_parts_sha256": ["def456"],
            }
            response = await rest_client.patch(
                f"/boxes/{box_id}/uploads/{file_id}",
                json=body,
                headers=close_file_token_header,
            )
        events = file_recorder.recorded_events
        assert len(events) == 1
        assert events[0].payload["state"] in ["inbox", "archived"]
        # Make sure the UCS-only fields are excluded from the outbox event
        assert not any(field in events[0].payload for field in FIELDS_NOT_PUBLISHED)

        # Let's lock the box now and verify that it is reflected in the event.
        # Box version is 1 after completing the file upload (stats changed 0→1 file).
        async with kafka.record_events(
            in_topic=config.file_upload_box_topic
        ) as box_recorder:
            lock_box_token_header = utils.change_file_box_token_header(
                box_id=box_id, jwk=rs_jwk
            )
            box_update_body = {"state": "locked", "version": 1}
            response = await rest_client.patch(
                f"/boxes/{box_id}", json=box_update_body, headers=lock_box_token_header
            )
            assert response.status_code == 204
        events = box_recorder.recorded_events
        assert len(events) == 1
        assert events[0].payload["state"] == "locked"

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

        # Great, we verified that the locked box prevents changes. Now unlock the box.
        # Box version is 2 after locking.
        box_update_body = {"state": "open", "version": 2}
        unlock_box_token_header = utils.change_file_box_token_header(
            box_id=box_id, work_type="unlock", jwk=rs_jwk
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

    The FileUpload and FileUploadBox are not updated, even though
    the S3 operations were finished properly. In this case, the requester would not
    receive a meaningful error message and would have to retry the request. Upon issuing
    the request a second time, the UCS would see that the S3 upload has already been
    completed and would then update the DB documents accordingly.
    """
    controller = joint_fixture.upload_controller
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )
    url = await controller.get_part_upload_url(file_id=file_id, part_no=1)

    # Upload the content
    response = await upload_to_s3(url, CONTENT)
    assert response.status_code == 200

    # To simulate the hiccup, we'll manually complete the upload. This will create the
    #  out-of-sync state described above.
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    file_upload_collection = db[FILE_UPLOADS_COLLECTION]
    uploads = file_upload_collection.find({"__metadata__.deleted": False}).to_list()
    assert len(uploads) == 1
    assert not uploads[0]["completed"]
    upload_id = uploads[0]["s3_upload_id"]
    object_id = str(uploads[0]["object_id"])

    await joint_fixture.s3.storage.complete_multipart_upload(
        bucket_id="test-inbox", object_id=object_id, upload_id=upload_id
    )

    # Now call the completion endpoint using the rest client
    close_token_header = utils.close_file_token_header(
        box_id=box_id, file_id=file_id, jwk=joint_fixture.wps_jwk
    )
    expected_encrypted_checksum = calc_expected_encrypted_checksum(CONTENT)
    body = {
        "decrypted_sha256": "abc123",
        "encrypted_md5": expected_encrypted_checksum,
        "encrypted_parts_md5": ["a1", "b2"],
        "encrypted_parts_sha256": ["a1", "b2"],
    }
    response = await joint_fixture.rest_client.patch(
        f"/boxes/{box_id}/uploads/{file_id}", json=body, headers=close_token_header
    )

    # Response should indicate success because the file was uploaded
    assert response.status_code == 204

    # DB should now show that everything is complete
    file_uploads = file_upload_collection.find(
        {"__metadata__.deleted": False}
    ).to_list()
    assert len(file_uploads) == 1
    assert file_uploads[0]["completed"]
    assert file_uploads[0]["state"] in ["inbox", "archived"]


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
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )
    url = await controller.get_part_upload_url(file_id=file_id, part_no=1)

    # Upload the content
    response = await upload_to_s3(url, CONTENT)
    assert response.status_code == 200

    # To simulate the hiccup, we'll manually abort the upload. This will create the
    #  out-of-sync state described above.
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    file_upload_collection = db[FILE_UPLOADS_COLLECTION]
    uploads = file_upload_collection.find({"__metadata__.deleted": False}).to_list()
    assert len(uploads) == 1
    assert not uploads[0]["completed"]
    upload_id = uploads[0]["s3_upload_id"]
    object_id = str(uploads[0]["object_id"])
    await joint_fixture.s3.storage.abort_multipart_upload(
        bucket_id="test-inbox", object_id=object_id, upload_id=upload_id
    )

    # Make the completion request with the rest client
    close_token_header = utils.close_file_token_header(
        box_id=box_id, file_id=file_id, jwk=wps_jwk
    )
    body: dict[str, Any] = {
        "decrypted_sha256": "abc123",
        "encrypted_md5": "abc123",
        "encrypted_parts_md5": ["a1", "b2"],
        "encrypted_parts_sha256": ["a1", "b2"],
    }
    response = await rest_client.patch(
        f"/boxes/{box_id}/uploads/{file_id}", json=body, headers=close_token_header
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
    body = {
        "alias": "test-file",
        "decrypted_size": DECRYPTED_SIZE,
        "encrypted_size": ENCRYPTED_SIZE,
        "part_size": utils.PART_SIZE,
    }
    response = await rest_client.post(
        f"/boxes/{box_id}/uploads", headers=create_token_header, json=body
    )
    assert response.status_code == 201
    file_creation_response_body = response.json()
    assert "file_id" in file_creation_response_body
    assert "alias" in file_creation_response_body
    assert "storage_alias" in file_creation_response_body
    file_id2 = UUID(file_creation_response_body["file_id"])
    assert "storage_alias" != ""
    assert file_creation_response_body["alias"] == body["alias"]

    upload_token_header = utils.upload_file_token_header(
        box_id=box_id, file_id=file_id2, jwk=wps_jwk
    )
    response = await rest_client.get(
        f"/boxes/{box_id}/uploads/{file_id2}/parts/1", headers=upload_token_header
    )
    assert response.status_code == 200
    part_url = response.json()

    # Upload the content again
    response = await upload_to_s3(part_url, CONTENT)
    assert response.status_code == 200
    expected_encrypted_checksum = calc_expected_encrypted_checksum(CONTENT)

    # Now complete the file
    close_token_header2 = utils.close_file_token_header(
        box_id=box_id, file_id=file_id2, jwk=wps_jwk
    )
    body = {
        "decrypted_sha256": "abc123",
        "encrypted_md5": expected_encrypted_checksum,
        "encrypted_parts_md5": ["abc123"],
        "encrypted_parts_sha256": ["def456"],
    }
    response = await rest_client.patch(
        f"/boxes/{box_id}/uploads/{file_id2}", json=body, headers=close_token_header2
    )
    assert response.status_code == 204

    # Check the DB to verify that docs were deleted for the old file upload and that
    #  the new file upload (for the same alias) exists instead, set to completed
    file_uploads = file_upload_collection.find(
        {"__metadata__.deleted": False}
    ).to_list()
    assert len(file_uploads) == 1
    assert file_uploads[0]["_id"] == file_id2
    assert file_uploads[0]["completed"]
    assert file_uploads[0]["state"] in ["inbox", "archived"]


async def test_orphaned_s3_upload_in_file_create(joint_fixture: JointFixture, caplog):
    """A test for the scenario where a crash occurs in the `init_file_upload` method
    between creating the S3 upload and inserting the FileUpload.

    The expected behavior is that the FileUpload is deleted, a critical error log
    is emitted, and the REST API returns a 409 CONFLICT error.
    """
    controller = joint_fixture.upload_controller
    s3_storage = joint_fixture.s3.storage
    bucket_id = joint_fixture.bucket_id

    # Create a box first
    correlation_id = uuid4()
    async with set_correlation_id(correlation_id):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )

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
    body = {
        "alias": "test-file",
        "decrypted_size": DECRYPTED_SIZE,
        "encrypted_size": ENCRYPTED_SIZE,
        "part_size": utils.PART_SIZE,
    }
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

    # Clean up the orphaned S3 upload for this test
    await s3_storage.abort_multipart_upload(
        bucket_id=bucket_id, object_id=str(file_id), upload_id=s3_upload_id
    )


async def test_file_upload_index(joint_fixture: JointFixture, monkeypatch):
    """Test that the compound FileUpload index works"""
    monkeypatch.setattr("ucs.main.Config", lambda: joint_fixture.config)

    async with set_correlation_id(uuid4()):
        box_id = await joint_fixture.upload_controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        _ = await joint_fixture.upload_controller.initiate_file_upload(
            box_id=box_id,
            alias="file1",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )
        with pytest.raises(UploadControllerPort.FileUploadAlreadyExists):
            _ = await joint_fixture.upload_controller.initiate_file_upload(
                box_id=box_id,
                alias="file1",
                decrypted_size=DECRYPTED_SIZE,
                encrypted_size=ENCRYPTED_SIZE,
                part_size=utils.PART_SIZE,
            )


async def test_file_interrogation_report_happy(joint_fixture: JointFixture):
    """Test the normal path of receiving an InterrogationSuccess event and deleting
    the file from the S3 bucket.

    This also checks that UCS doesn't try to delete the interrogated file from the
    interrogation bucket.
    """
    controller = joint_fixture.upload_controller
    s3_storage = joint_fixture.s3.storage
    inbox_bucket_id = joint_fixture.bucket_id
    config = joint_fixture.config

    # Create a box and initiate a file upload
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )

    # Get upload URL and upload the file content
    url = await controller.get_part_upload_url(file_id=file_id, part_no=1)
    response = await upload_to_s3(url, CONTENT)
    expected_encrypted_checksum = calc_expected_encrypted_checksum(CONTENT)
    assert response.status_code == 200

    # Complete the file upload
    async with set_correlation_id(uuid4()):
        await controller.complete_file_upload(
            box_id=box_id,
            file_id=file_id,
            unencrypted_checksum="abc123",
            encrypted_checksum=expected_encrypted_checksum,
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    # Look up the actual object_id from the DB (independent from file_id)
    db = joint_fixture.mongodb.client[config.db_name]
    file_upload_collection = db[FILE_UPLOADS_COLLECTION]
    file_upload_db = file_upload_collection.find_one(
        {"_id": file_id, "__metadata__.deleted": False}
    )
    assert file_upload_db is not None
    object_id = str(file_upload_db["object_id"])

    # Verify the file exists in S3
    file_exists_before = await s3_storage.does_object_exist(
        bucket_id=inbox_bucket_id, object_id=object_id
    )
    assert file_exists_before

    # Verify the database records exist
    file_uploads_before = file_upload_collection.find(
        {"_id": file_id, "__metadata__.deleted": False}
    ).to_list()
    assert len(file_uploads_before) == 1
    assert file_uploads_before[0]["completed"]
    assert file_uploads_before[0]["state"] == "inbox"

    # Create and publish an InterrogationSuccess event
    interrogation_bucket_id = "interrogation"
    interrogated_object_id = uuid4()
    interrogation_success = InterrogationSuccess(
        file_id=file_id,
        secret_id="test-secret-123",
        storage_alias="test",
        bucket_id=interrogation_bucket_id,
        object_id=interrogated_object_id,
        interrogated_at=now_utc_ms_prec(),
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
        encrypted_size=ENCRYPTED_SIZE,
    )

    # Put an object into the interrogation bucket to simulate DHFS's work
    await s3_storage.create_bucket(interrogation_bucket_id)
    upload_id = await s3_storage.init_multipart_upload(
        bucket_id=interrogation_bucket_id,
        object_id=str(interrogated_object_id),
    )
    upload_url = await s3_storage.get_part_upload_url(
        upload_id=upload_id,
        bucket_id=interrogation_bucket_id,
        object_id=str(interrogated_object_id),
        part_number=1,
    )
    response = await upload_to_s3(upload_url, b"some content does not matter what")
    assert response.status_code == 200, "Failed to upload dummy re-encrypted object"
    await s3_storage.complete_multipart_upload(
        upload_id=upload_id,
        bucket_id=interrogation_bucket_id,
        object_id=str(interrogated_object_id),
    )
    # Need to double check that the object is there before proceeding
    interrogation_file_exists = await s3_storage.does_object_exist(
        bucket_id=interrogation_bucket_id, object_id=str(interrogated_object_id)
    )
    assert interrogation_file_exists, "Dummy object not present in interrogation bucket"

    # REGRESSION TEST: Verify that an S3 error doesn't result in an orphaned inbox object
    _real_get_storage_fn = controller._s3_client._get_bucket_and_storage
    _real_delete_fn = s3_storage.delete_object

    async def _erroring_delete_fn(*, bucket_id: str, object_id: str) -> None:
        raise s3_storage.ObjectStorageProtocolError("problem")

    s3_storage.delete_object = _erroring_delete_fn
    controller._s3_client._get_bucket_and_storage = lambda x: (
        inbox_bucket_id,
        s3_storage,
    )

    # Publish/consume the InterrogationSuccess event to trigger S3 error
    await joint_fixture.kafka.publish_event(
        payload=interrogation_success.model_dump(mode="json"),
        type_=config.interrogation_success_type,
        topic=config.file_interrogations_topic,
    )
    with pytest.raises(UploadControllerPort.S3OperationError):
        await joint_fixture.event_subscriber.run(forever=False)

    # Verify that the the FileUpload is unchanged and the object is still in the inbox
    await s3_storage.does_object_exist(bucket_id=inbox_bucket_id, object_id=object_id)
    file_upload_check = file_upload_collection.find_one({"_id": file_id})
    assert file_upload_check is not None
    assert file_upload_check["state"] == "inbox"
    assert file_upload_check["object_id"] == UUID(object_id)

    # Undo the S3 patches. This is the end of the regression test
    s3_storage.delete_object = _real_delete_fn
    controller._s3_client._get_bucket_and_storage = _real_get_storage_fn

    # Now we can publish the InterrogationSuccess event for real
    await joint_fixture.kafka.publish_event(
        payload=interrogation_success.model_dump(mode="json"),
        type_=config.interrogation_success_type,
        topic=config.file_interrogations_topic,
    )

    # Consume the event
    await joint_fixture.event_subscriber.run(forever=False)

    # Verify the file has been deleted from the inbox but NOT from interrogation
    file_exists_after = await s3_storage.does_object_exist(
        bucket_id=inbox_bucket_id, object_id=object_id
    )
    assert not file_exists_after, "Object was not deleted from inbox like it should be"

    interrogation_file_exists = await s3_storage.does_object_exist(
        bucket_id=interrogation_bucket_id, object_id=str(interrogated_object_id)
    )
    assert interrogation_file_exists, "Object was deleted from interrogation bucket"

    # Verify the FileUpload state was updated
    file_uploads_after = file_upload_collection.find().to_list()
    assert len(file_uploads_after) == 1
    assert file_uploads_after[0]["state"] == "interrogated"

    # Now test for idempotency by repeating the publish and consume
    await joint_fixture.kafka.publish_event(
        payload=interrogation_success.model_dump(mode="json"),
        type_=config.interrogation_success_type,
        topic=config.file_interrogations_topic,
    )

    # Consume the event -- should not receive an error
    await joint_fixture.event_subscriber.run(forever=False)


async def test_file_deletion_requested_event(joint_fixture: JointFixture, caplog):
    """Test that consuming a FileDeletionRequested event aborts the S3 multipart upload
    and marks the FileUpload as 'cancelled'.

    Also verifies behavior for publishing a deletion event for an unknown file ID
    (should be consumed without error).
    """
    controller = joint_fixture.upload_controller
    config = joint_fixture.config
    db = joint_fixture.mongodb.client[config.db_name]
    file_upload_collection = db[FILE_UPLOADS_COLLECTION]

    # Create a FileUpload with an active MPU
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )

    # Publish the file deletion request event
    event = FileDeletionRequested(file_id=file_id)
    await joint_fixture.kafka.publish_event(
        payload=event.model_dump(mode="json"),
        type_=config.file_deletion_request_type,
        topic=config.file_deletion_request_topic,
    )

    # Consume it
    await joint_fixture.event_subscriber.run(forever=False)

    # Check that the item is set to 'cancelled'
    file_uploads_after = file_upload_collection.find({"_id": file_id}).to_list()
    assert len(file_uploads_after) == 1
    assert file_uploads_after[0]["state"] == "cancelled"

    # Consume the same event again
    await joint_fixture.kafka.publish_event(
        payload=event.model_dump(mode="json"),
        type_=config.file_deletion_request_type,
        topic=config.file_deletion_request_topic,
    )
    with caplog.at_level("INFO"):
        caplog.clear()
        await joint_fixture.event_subscriber.run(forever=False)
    assert any(
        f"FileUpload {file_id} is already marked 'cancelled', further action presumed unnecessary."
        in record.message
        for record in caplog.records
    )

    # Publish/Consume a deletion request for a file that doesn't exist (no error)
    unknown_event = FileDeletionRequested(file_id=uuid4())
    await joint_fixture.kafka.publish_event(
        payload=unknown_event.model_dump(mode="json"),
        type_=config.file_deletion_request_type,
        topic=config.file_deletion_request_topic,
    )
    with caplog.at_level("WARNING"):
        caplog.clear()
        await joint_fixture.event_subscriber.run(forever=False)
    assert any(
        f"Cannot process deletion request for file ID {unknown_event.file_id}. No such FileUpload found."
        in record.message
        for record in caplog.records
    )


async def test_cleanup_aborts_orphaned_s3_uploads(
    joint_fixture: JointFixture, monkeypatch: pytest.MonkeyPatch
):
    """Test that the cleanup job aborts S3 multipart uploads with no corresponding
    FileUpload record, while leaving recently-initiated uploads untouched.
    """
    controller = joint_fixture.upload_controller
    s3_storage = joint_fixture.s3.storage
    bucket_id = joint_fixture.bucket_id

    # Create a genuinely orphaned S3 multipart upload (no FileUpload DB record)
    orphaned_object_id = str(uuid4())
    orphaned_s3_upload_id = await s3_storage.init_multipart_upload(
        bucket_id=bucket_id, object_id=orphaned_object_id
    )

    # Also create a proper FileUpload (recent — well within the TTL)
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )

    # Both uploads should be active before cleanup
    active_uploads_before = await s3_storage.get_all_multipart_uploads(
        bucket_id=bucket_id
    )
    assert orphaned_s3_upload_id in active_uploads_before
    assert len(active_uploads_before) == 2

    # Run the cleanup job (patch prepare_core to return our test object)
    @asynccontextmanager
    async def _prepare_core(config):
        yield joint_fixture.upload_controller

    monkeypatch.setattr("ucs.main.prepare_core", _prepare_core)
    await perform_cleanup(run_forever=False)

    # The orphaned upload should be aborted
    active_uploads_after = await s3_storage.get_all_multipart_uploads(
        bucket_id=bucket_id
    )
    assert orphaned_s3_upload_id not in active_uploads_after

    # The recent FileUpload should remain in "init" state (not cancelled)
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    file_upload_doc = db[FILE_UPLOADS_COLLECTION].find_one({"_id": file_id})
    assert file_upload_doc is not None
    assert file_upload_doc["state"] == "init"

    # Verify that the active upload is still alive in S3
    assert file_upload_doc["s3_upload_id"] in active_uploads_after


async def test_cleanup_cancels_despite_s3_abort_failure(
    joint_fixture: JointFixture, monkeypatch: pytest.MonkeyPatch
):
    """Test that the cleanup job marks a stale upload as 'cancelled' even when the
    S3 abort call raises an error, and that the orphaned S3 upload is cleaned up on
    the next run.

    This is an integration-test-copy of the unit test by the same name, but this one
    follows up by running the job a final time to ensure the upload is ultimately
    cleaned up.
    """
    controller = joint_fixture.upload_controller
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    s3_storage = joint_fixture.s3.storage
    bucket_id = joint_fixture.bucket_id

    # Create a box and initiate a file upload
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )

    # Backdate the activity entry so the upload appears stale (beyond the 72h TTL)
    stale_timestamp = now_utc_ms_prec() - timedelta(hours=73)
    db[UPLOAD_ACTIVITY_COLLECTION].update_one(
        {"_id": file_id}, {"$set": {"last_activity": stale_timestamp}}
    )

    # Get S3 details from the DB and patch abort_multipart_upload to raise an error
    file_upload_doc = db[FILE_UPLOADS_COLLECTION].find_one({"_id": file_id})
    assert file_upload_doc is not None
    s3_upload_id = file_upload_doc["s3_upload_id"]
    s3_client = joint_fixture.upload_controller._s3_client

    async def failing_abort(**kwargs):
        raise s3_client.S3UploadAbortError(
            s3_upload_id=s3_upload_id,
            object_id=str(file_upload_doc["object_id"]),
            bucket_id=file_upload_doc["bucket_id"],
        )

    monkeypatch.setattr(s3_client, "abort_multipart_upload", failing_abort)

    # Run the cleanup job (patch prepare_core to return our test object)
    @asynccontextmanager
    async def _prepare_core(config):
        yield joint_fixture.upload_controller

    monkeypatch.setattr("ucs.main.prepare_core", _prepare_core)
    await perform_cleanup(run_forever=False)

    # The FileUpload should be marked 'cancelled' despite the S3 failure
    file_upload_doc = db[FILE_UPLOADS_COLLECTION].find_one({"_id": file_id})
    assert file_upload_doc is not None
    assert file_upload_doc["state"] == "cancelled"

    # The activity entry should have been removed
    assert db[UPLOAD_ACTIVITY_COLLECTION].find_one({"_id": file_id}) is None

    # The S3 multipart upload should still be alive (the abort failed)
    uploads = await s3_storage.get_all_multipart_uploads(bucket_id=bucket_id)
    assert s3_upload_id in uploads

    # Undo the patch and run cleanup again — the leftover upload is now an orphan
    # (no FileUpload in 'init' state) and should be aborted
    monkeypatch.undo()
    await controller.cleanup_stale_uploads()

    uploads = await s3_storage.get_all_multipart_uploads(bucket_id=bucket_id)
    assert s3_upload_id not in uploads


@pytest.mark.parametrize("simulate_errors", [True, False])
async def test_cleanup_of_orphaned_files(
    joint_fixture: JointFixture, simulate_errors: bool, caplog
):
    """Test that orphaned files are deleted from the inbox by the cleanup job."""
    controller = joint_fixture.upload_controller
    s3_storage = joint_fixture.s3.storage
    bucket_id = joint_fixture.bucket_id

    # Create a box and initiate a file upload
    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_init_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file1",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )
        file_inbox_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file2",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )
        file_cancelled_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file3",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )
    for file_id in [file_init_id, file_inbox_id, file_cancelled_id]:
        url = await controller.get_part_upload_url(file_id=file_id, part_no=1)
        await upload_to_s3(url, b"some-data")

    # Complete the uploads
    collection = joint_fixture.mongodb.client[joint_fixture.config.db_name][
        FILE_UPLOADS_COLLECTION
    ]
    file_init_doc = collection.find_one({"_id": file_init_id})
    file_inbox_doc = collection.find_one({"_id": file_inbox_id})
    file_cancelled_doc = collection.find_one({"_id": file_cancelled_id})
    assert file_init_doc is not None
    assert file_inbox_doc is not None
    assert file_cancelled_doc is not None
    file_init_object_id = str(file_init_doc["object_id"])
    file_inbox_object_id = str(file_inbox_doc["object_id"])
    file_cancelled_object_id = str(file_cancelled_doc["object_id"])
    await s3_storage.complete_multipart_upload(
        upload_id=file_init_doc["s3_upload_id"],
        bucket_id=bucket_id,
        object_id=file_init_object_id,
    )
    await s3_storage.complete_multipart_upload(
        upload_id=file_inbox_doc["s3_upload_id"],
        bucket_id=bucket_id,
        object_id=file_inbox_object_id,
    )
    await s3_storage.complete_multipart_upload(
        upload_id=file_cancelled_doc["s3_upload_id"],
        bucket_id=bucket_id,
        object_id=file_cancelled_object_id,
    )

    # Set the inbox and cancelled docs to the desired states but leave init as is to
    #  simulate race condition
    file_inbox_doc["inbox"] = "inbox"
    file_cancelled_doc["state"] = "cancelled"
    collection.replace_one(filter={"_id": file_inbox_id}, replacement=file_inbox_doc)
    collection.replace_one(
        filter={"_id": file_cancelled_id}, replacement=file_cancelled_doc
    )

    # Upload two different orphaned objects
    orphaned_object_id1 = str(uuid4())
    orphaned_object_id2 = "not-a-uuid"
    for object_id in [orphaned_object_id1, orphaned_object_id2]:
        upload_id = await s3_storage.init_multipart_upload(
            bucket_id=bucket_id, object_id=object_id
        )
        url = await s3_storage.get_part_upload_url(
            upload_id=upload_id, bucket_id=bucket_id, object_id=object_id, part_number=1
        )
        await upload_to_s3(url, b"some-data")
        await s3_storage.complete_multipart_upload(
            upload_id=upload_id, bucket_id=bucket_id, object_id=object_id
        )

    # Check the list of current IDs before running the job
    all_object_ids = await s3_storage.list_all_object_ids(bucket_id=bucket_id)
    assert set(all_object_ids) == {
        file_init_object_id,
        file_inbox_object_id,
        file_cancelled_object_id,
        orphaned_object_id1,
        orphaned_object_id2,
    }

    # Simulate errors in the S3 delete method if simulate_errors is True
    _real_deletion_method = s3_storage.delete_object

    class _S3PermissionError(ObjectStorageProtocol.ObjectStorageProtocolError):
        def __init__(self, *, bucket_id: str, object_id: str):
            super().__init__("You don't have permission to do that.")

    async def _delete_with_error(bucket_id: str, object_id: str) -> None:
        """Raises an _S3PermissionError for one object, deletes the rest normally."""
        if object_id == file_cancelled_object_id:
            raise _S3PermissionError(bucket_id=bucket_id, object_id=object_id)
        return await _real_deletion_method(bucket_id=bucket_id, object_id=object_id)

    if simulate_errors:
        s3_storage.delete_object = _delete_with_error
        controller._s3_client._get_bucket_and_storage = lambda x: (
            bucket_id,
            s3_storage,
        )

    # Run the cleanup job
    caplog.clear()
    with caplog.at_level("INFO"):
        await controller.cleanup_stale_uploads()

    deleted_count = 2 if simulate_errors else 3
    log_msg = (
        f"Cleaned up {deleted_count} orphaned object(s) from bucket {bucket_id}"
        + " in storage alias test."
    )

    if simulate_errors:
        log_msg += " An additional 1 object(s) could not be deleted."
    assert log_msg in caplog.messages

    # Verify that the orphaned and cancelled files are gone, but init and inbox remain
    all_object_ids = await s3_storage.list_all_object_ids(bucket_id=bucket_id)

    expected_objects = {file_init_object_id, file_inbox_object_id}
    if simulate_errors:
        expected_objects.add(file_cancelled_object_id)  # didn't get deleted due to exc
    assert set(all_object_ids) == expected_objects


async def test_upload_activity_deleted_after_completion_failure(
    joint_fixture: JointFixture,
):
    """Test that the UploadActivity entry is deleted when remove_file_upload is called
    after a failed completion due to a checksum mismatch.
    """
    controller = joint_fixture.upload_controller
    config = joint_fixture.config
    db = joint_fixture.mongodb.client[config.db_name]
    upload_activity_collection = db[UPLOAD_ACTIVITY_COLLECTION]

    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_id, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )

    # Verify the activity entry was created
    assert upload_activity_collection.find_one({"_id": file_id}) is not None

    # Upload content and attempt completion with a wrong checksum
    url = await controller.get_part_upload_url(file_id=file_id, part_no=1)
    response = await upload_to_s3(url, CONTENT)
    assert response.status_code == 200

    async with set_correlation_id(uuid4()):
        with pytest.raises(UploadControllerPort.ChecksumMismatchError):
            await controller.complete_file_upload(
                box_id=box_id,
                file_id=file_id,
                unencrypted_checksum="abc",
                encrypted_checksum="definitely-wrong-checksum",
                encrypted_parts_md5=["abc"],
                encrypted_parts_sha256=["def"],
            )

    # The activity entry should still exist after the failed completion
    assert upload_activity_collection.find_one({"_id": file_id}) is not None

    # The FileUpload should be in "failed" state
    file_upload_doc = db[FILE_UPLOADS_COLLECTION].find_one({"_id": file_id})
    assert file_upload_doc is not None
    assert file_upload_doc["state"] == "failed"

    # Deleting the upload should clean up the activity entry
    async with set_correlation_id(uuid4()):
        await controller.remove_file_upload(box_id=box_id, file_id=file_id)

    assert upload_activity_collection.find_one({"_id": file_id}) is None


async def test_deletion_of_multiple_files(joint_fixture: JointFixture):
    """Test that the sparse index prevents index collisions for multiple deleted items
    in a single box.
    """
    controller = joint_fixture.upload_controller

    async with set_correlation_id(uuid4()):
        box_id = await controller.create_file_upload_box(
            storage_alias="test", max_size=utils.TEST_MAX_BOX_SIZE
        )
        file_id1, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file1",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )
        file_id2, _ = await controller.initiate_file_upload(
            box_id=box_id,
            alias="test-file2",
            decrypted_size=DECRYPTED_SIZE,
            encrypted_size=ENCRYPTED_SIZE,
            part_size=utils.PART_SIZE,
        )

        # Delete the files. No error means success
        await controller._file_upload_dao.delete(file_id1)
        await controller._file_upload_dao.delete(file_id2)
