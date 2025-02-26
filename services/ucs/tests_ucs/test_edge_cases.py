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

"""Test edge cases of interacting with the services API.

Note: This test module uses the module-scoped fixtures.
"""

import json
from contextlib import suppress

import pytest
from fastapi import status
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.dao import ResourceNotFoundError
from hexkit.providers.s3.testutils import upload_part_via_url
from logot import Logot, logged

from tests_ucs.fixtures.example_data import UPLOAD_DETAILS_1
from tests_ucs.fixtures.joint import JointFixture
from ucs.core import models

pytestmark = pytest.mark.asyncio()


async def create_multipart_upload_with_data(
    joint_fixture: JointFixture,
    file_to_register: event_schemas.MetadataSubmissionFiles,
    storage_alias: str,
):
    """Run upload process until first part is uploaded and status remains in pending."""
    # publish event to register a new file for upload:
    file_metadata_event = event_schemas.MetadataSubmissionUpserted(
        associated_files=[file_to_register]
    )
    await joint_fixture.kafka.publish_event(
        payload=file_metadata_event.model_dump(),
        type_=joint_fixture.config.file_metadata_event_type,
        topic=joint_fixture.config.file_metadata_event_topic,
    )
    # consume the event:
    await joint_fixture.event_subscriber.run(forever=False)

    file_id = file_to_register.file_id
    # initiate new upload:
    response = await joint_fixture.rest_client.post(
        "/uploads",
        json={
            "file_id": file_id,
            "submitter_public_key": "test-key",
            "storage_alias": storage_alias,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    upload_details = response.json()

    # request an upload URL for a part:
    response = await joint_fixture.rest_client.post(
        f"/uploads/{upload_details['upload_id']}/parts/1/signed_urls"
    )
    assert response.status_code == status.HTTP_200_OK
    part_upload_details = response.json()

    # upload a file part with arbitrary content
    upload_part_via_url(
        url=part_upload_details["url"], size=upload_details["part_size"]
    )

    return upload_details["object_id"]


async def test_get_health(joint_fixture: JointFixture):
    """Test the GET /health endpoint.

    reset_state fixture isn't needed because the test is unaffected by state.
    """
    response = await joint_fixture.rest_client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


async def test_get_file_metadata_not_found(joint_fixture: JointFixture):
    """Test the get_file_metadata endpoint with an non-existing file id."""
    file_id = "myNonExistingFile001"
    response = await joint_fixture.rest_client.get(f"/files/{file_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["exception_id"] == "fileNotRegistered"


async def test_create_upload_not_found(joint_fixture: JointFixture):
    """Test the create_upload endpoint with an non-existing file id."""
    file_id = "myNonExistingFile001"
    response = await joint_fixture.rest_client.post(
        "/uploads",
        json={
            "file_id": file_id,
            "submitter_public_key": "test-key",
            "storage_alias": UPLOAD_DETAILS_1.storage_alias,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["exception_id"] == "fileNotRegistered"


@pytest.mark.parametrize(
    "existing_status",
    [
        status_
        for status_ in [
            models.UploadStatus.PENDING,
            models.UploadStatus.UPLOADED,
            models.UploadStatus.ACCEPTED,
        ]
    ],
)
async def test_create_upload_other_active(
    existing_status: models.UploadStatus,
    joint_fixture: JointFixture,
):
    """Test the create_upload endpoint when there is another active update already
    existing.
    """
    existing_upload = UPLOAD_DETAILS_1.upload_attempt.model_copy(
        update={"status": existing_status}
    )

    # insert a pending upload into the database:
    await joint_fixture.daos.file_metadata.insert(UPLOAD_DETAILS_1.file_metadata)
    await joint_fixture.daos.upload_attempts.insert(existing_upload)

    response = await joint_fixture.rest_client.post(
        "/uploads",
        json={
            "file_id": UPLOAD_DETAILS_1.file_metadata.file_id,
            "submitter_public_key": "test-key",
            "storage_alias": UPLOAD_DETAILS_1.storage_alias,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_body = response.json()
    assert response_body["exception_id"] == "existingActiveUpload"
    assert response_body["data"]["active_upload"] == json.loads(
        existing_upload.model_dump_json()
    )


@pytest.mark.parametrize(
    "existing_status",
    [
        models.UploadStatus.UPLOADED,
        models.UploadStatus.ACCEPTED,
    ],
)
async def test_create_upload_accepted(
    existing_status: models.UploadStatus,
    joint_fixture: JointFixture,
):
    """Test the create_upload endpoint when another update has already been accepted
    or is currently being evaluated.
    """
    existing_upload = UPLOAD_DETAILS_1.upload_attempt.model_copy(
        update={"status": existing_status}
    )

    # insert the existing upload into the database:
    await joint_fixture.daos.file_metadata.insert(UPLOAD_DETAILS_1.file_metadata)
    await joint_fixture.daos.upload_attempts.insert(existing_upload)

    # try to create a new upload:
    response = await joint_fixture.rest_client.post(
        "/uploads",
        json={
            "file_id": UPLOAD_DETAILS_1.file_metadata.file_id,
            "submitter_public_key": "test-key",
            "storage_alias": UPLOAD_DETAILS_1.storage_alias,
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_body = response.json()
    assert response_body["exception_id"] == "existingActiveUpload"
    assert response_body["data"]["active_upload"] == json.loads(
        existing_upload.model_dump_json()
    )


async def test_create_upload_unknown_storage(joint_fixture: JointFixture):
    """Test the create_upload endpoint with storage_alias missing in the request body"""
    # insert upload metadata into the database:
    await joint_fixture.daos.file_metadata.insert(UPLOAD_DETAILS_1.file_metadata)

    # try to create a new upload:
    response = await joint_fixture.rest_client.post(
        "/uploads",
        json={
            "file_id": UPLOAD_DETAILS_1.file_metadata.file_id,
            "submitter_public_key": "test-key",
            "storage_alias": "absolutely_fake_alias",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_body = response.json()
    assert response_body["exception_id"] == "noSuchStorage"


async def test_get_upload_not_found(joint_fixture: JointFixture):
    """Test the get_upload endpoint with non-existing upload ID."""
    upload_id = "myNonExistingUpload001"
    response = await joint_fixture.rest_client.get(f"/uploads/{upload_id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["exception_id"] == "noSuchUpload"


async def test_update_upload_status_not_found(joint_fixture: JointFixture):
    """Test the update_upload_status endpoint with non existing upload ID."""
    upload_id = "myNonExistingUpload001"

    response = await joint_fixture.rest_client.patch(
        f"/uploads/{upload_id}", json={"status": models.UploadStatus.CANCELLED.value}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["exception_id"] == "noSuchUpload"


@pytest.mark.parametrize(
    "new_status",
    [
        status_
        for status_ in models.UploadStatus
        if status_ not in [models.UploadStatus.CANCELLED, models.UploadStatus.UPLOADED]
    ],
)
async def test_update_upload_status_invalid_new_status(
    new_status: models.UploadStatus,
    joint_fixture: JointFixture,
):
    """Test the update_upload_status endpoint with invalid new status values."""
    upload_id = "myNonExistingUpload001"
    # (Input data validation should happen before checking the existence of the
    # specified resource, thus a non existing upload ID can be used here.)

    response = await joint_fixture.rest_client.patch(
        f"/uploads/{upload_id}", json={"status": new_status.value}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "old_status",
    [
        status_
        for status_ in models.UploadStatus
        if status_ != models.UploadStatus.PENDING
    ],
)
async def test_update_upload_status_non_pending(
    old_status: models.UploadStatus,
    joint_fixture: JointFixture,
):
    """Test the update_upload_status endpoint on non pending upload."""
    target_upload = UPLOAD_DETAILS_1.upload_attempt.model_copy(
        update={"status": old_status}
    )

    # insert a pending and non_pending upload into the database:
    await joint_fixture.daos.file_metadata.insert(UPLOAD_DETAILS_1.file_metadata)
    await joint_fixture.daos.upload_attempts.insert(target_upload)

    for new_status in [models.UploadStatus.CANCELLED, models.UploadStatus.UPLOADED]:
        response = await joint_fixture.rest_client.patch(
            f"/uploads/{target_upload.upload_id}", json={"status": new_status.value}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_body = response.json()
        assert response_body["exception_id"] == "uploadNotPending"
        assert response_body["data"]["current_upload_status"] == old_status.value


async def test_create_presigned_url_not_found(joint_fixture: JointFixture):
    """Test the create_presigned_url endpoint with non existing upload ID."""
    upload_id = "myNonExistingUpload001"

    response = await joint_fixture.rest_client.post(
        f"/uploads/{upload_id}/parts/{1}/signed_urls"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["exception_id"] == "noSuchUpload"


async def test_deletion_upload_ongoing(joint_fixture: JointFixture):
    """Test file data deletion while upload is still ongoing.

    This mainly tests if abort multipart upload worked correctly in the deletion context.
    """
    storage_alias = UPLOAD_DETAILS_1.storage_alias
    file_to_register = UPLOAD_DETAILS_1.submission_metadata
    file_id = file_to_register.file_id

    inbox_object_id = await create_multipart_upload_with_data(
        joint_fixture=joint_fixture,
        file_to_register=file_to_register,
        storage_alias=storage_alias,
    )

    # Verify everything that should exist is present
    assert not await joint_fixture.s3.storage.does_object_exist(
        bucket_id=joint_fixture.bucket_id, object_id=inbox_object_id
    )
    with suppress(joint_fixture.s3.storage.MultiPartUploadAlreadyExistsError):
        await joint_fixture.s3.storage._assert_no_multipart_upload(
            bucket_id=joint_fixture.bucket_id, object_id=inbox_object_id
        )
    assert await joint_fixture.daos.file_metadata.get_by_id(id_=file_id)

    num_attempts = 0
    async for _ in joint_fixture.daos.upload_attempts.find_all(
        mapping={"file_id": file_id}
    ):
        num_attempts += 1
    assert num_attempts == 1

    # Request deletion
    deletion_event = event_schemas.FileDeletionRequested(file_id=file_id)
    await joint_fixture.kafka.publish_event(
        payload=json.loads(deletion_event.model_dump_json()),
        type_="upserted",
        topic=joint_fixture.config.files_to_delete_topic,
    )

    # Consume inbound event and check outbound event
    deletion_successful_event = event_schemas.FileDeletionSuccess(file_id=file_id)
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_deleted_event_topic
    ) as recorder:
        await joint_fixture.event_subscriber.run(forever=False)

    assert len(recorder.recorded_events) == 1
    assert recorder.recorded_events[0].payload == deletion_successful_event.model_dump()

    # Verify everything is gone
    assert not await joint_fixture.s3.storage.does_object_exist(
        bucket_id=joint_fixture.bucket_id, object_id=inbox_object_id
    )
    await joint_fixture.s3.storage._assert_no_multipart_upload(
        bucket_id=joint_fixture.bucket_id, object_id=inbox_object_id
    )
    with suppress(ResourceNotFoundError):
        await joint_fixture.daos.file_metadata.get_by_id(id_=file_id)

    num_attempts = 0
    async for _ in joint_fixture.daos.upload_attempts.find_all(
        mapping={"file_id": file_id}
    ):
        num_attempts += 1
    assert num_attempts == 0


async def test_deletion_with_no_file(joint_fixture: JointFixture):
    """This should be the same as processing FileDeletionRequested repeats."""
    file_id = "aint_no_such"
    deletion_event = event_schemas.FileDeletionRequested(file_id=file_id)
    await joint_fixture.kafka.publish_event(
        payload=json.loads(deletion_event.model_dump_json()),
        type_="upserted",
        topic=joint_fixture.config.files_to_delete_topic,
    )

    # Consume inbound event
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_deleted_event_topic
    ) as recorder:
        await joint_fixture.upload_service.deletion_requested(file_id=file_id)

    # Check for event
    assert len(recorder.recorded_events) == 0


async def test_deletion_logs(joint_fixture: JointFixture, logot: Logot):
    """Test that the outbox subscriber logs deletions correctly.
    Consume a 'DELETED' event type for the outbox event.
    """
    file_id = "file_id123"
    # publish test event
    await joint_fixture.kafka.publish_event(
        payload=event_schemas.FileDeletionSuccess(file_id=file_id).model_dump(),
        type_="deleted",
        topic=joint_fixture.config.files_to_delete_topic,
        key=file_id,
    )
    # consume that event
    await joint_fixture.event_subscriber.run(forever=False)

    # verify the log
    logot.assert_logged(
        logged.warning(
            "Received DELETED-type event for FileDeletionRequested"
            + f" with resource ID '{file_id}'",
        )
    )
