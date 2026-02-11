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

"""Testing for listening to FileUploadBox events"""

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from ghga_service_commons.auth.ghga import AuthContext
from hexkit.utils import now_utc_ms_prec
from pytest_httpx import HTTPXMock

from tests.fixtures.joint import JointFixture
from uos.core.models import AccessionMapRequest, UpdateUploadBoxRequest

pytestmark = pytest.mark.asyncio


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_typical_journey(joint_fixture: JointFixture, httpx_mock: HTTPXMock):
    """Test the path that involves:
    - Creating a box
    - Granting a user access to said box
    - Updating the title or description of the box
    - Receiving a FileUploadBox update event from kafka (which belongs to the box)
    - Querying the box
    - Checking if a user has access to the box
    - Setting the state to LOCKED
    """
    # Test data
    file_box_service_url = joint_fixture.config.ucs_url
    access_url = joint_fixture.config.access_url
    ds_user_id = uuid4()
    regular_user_id = uuid4()
    iva_id = uuid4()
    file_upload_box_id = uuid4()
    audit_topic = joint_fixture.config.audit_record_topic
    research_box_topic = joint_fixture.config.research_data_upload_box_topic

    # Shorthand reference to the orchestrator
    orchestrator = joint_fixture.upload_orchestrator

    # Create auth contexts
    iat = now_utc_ms_prec() - timedelta(hours=1)

    user_auth_context = AuthContext(
        id=str(regular_user_id),
        name="Regular User",
        email="user@test.com",
        iat=iat,
        exp=iat + timedelta(hours=24),
    )

    ds_auth_context = AuthContext(
        id=str(ds_user_id),
        name="Data Steward",
        email="user@test.com",
        iat=iat,
        exp=iat + timedelta(hours=24),
        roles=["data_steward"],
    )

    # Create a box (requires data steward)
    httpx_mock.add_response(
        method="POST",
        url=f"{file_box_service_url}/boxes",
        status_code=201,
        json=str(file_upload_box_id),
    )
    async with (
        joint_fixture.kafka.record_events(in_topic=audit_topic) as audit_event_recorder,
        joint_fixture.kafka.record_events(
            in_topic=research_box_topic
        ) as box_event_recorder,
    ):
        box_id = await orchestrator.create_research_data_upload_box(
            title="Test Box",
            description="A test upload box",
            storage_alias="test-storage",
            data_steward_id=ds_user_id,
        )
    assert audit_event_recorder.recorded_events
    audit_event = audit_event_recorder.recorded_events[0]
    assert audit_event.payload["label"] == "ResearchDataUploadBox created"  # suffices
    assert box_id is not None
    assert box_event_recorder.recorded_events
    assert len(box_event_recorder.recorded_events) == 1
    assert box_event_recorder.recorded_events[0].payload["id"] == str(box_id)

    # Grant a user access to said box
    httpx_mock.add_response(
        method="POST",
        url=f"{access_url}/upload-access/users/{regular_user_id}/ivas/{iva_id}/boxes/{box_id}",
        status_code=200,
    )
    valid_from = now_utc_ms_prec()
    valid_until = now_utc_ms_prec() + timedelta(days=7)
    await orchestrator.grant_upload_access(
        user_id=regular_user_id,
        iva_id=iva_id,
        box_id=box_id,
        valid_from=valid_from,
        valid_until=valid_until,
        granting_user_id=ds_user_id,
    )

    # Update the title or description of the box by a DS (this bumps version to 1)
    update_request = UpdateUploadBoxRequest(
        version=0,  # Initial version
        title="Updated Test Box",
        description="Updated description",
    )
    async with (
        joint_fixture.kafka.record_events(in_topic=audit_topic) as audit_event_recorder,
        joint_fixture.kafka.record_events(
            in_topic=research_box_topic
        ) as box_event_recorder,
    ):
        await orchestrator.update_research_data_upload_box(
            box_id=box_id,
            request=update_request,
            auth_context=ds_auth_context,
        )
    assert audit_event_recorder.recorded_events
    audit_event = audit_event_recorder.recorded_events[0]
    assert audit_event.payload["label"] == "ResearchDataUploadBox updated"
    assert box_event_recorder.recorded_events
    assert len(box_event_recorder.recorded_events) == 1
    assert box_event_recorder.recorded_events[0].payload["title"] == "Updated Test Box"

    # Receive a FileUploadBox update event from kafka (which belongs to the box)
    # This bumps version to 2
    file_upload_box_event: dict[str, Any] = {
        "id": str(file_upload_box_id),
        "version": 1,
        "state": "open",
        "file_count": 1,
        "size": 1024000,
        "storage_alias": "test-storage",
    }

    await joint_fixture.kafka.publish_event(
        payload=file_upload_box_event,
        type_="upserted",
        topic=joint_fixture.config.file_upload_box_topic,
        key=str(file_upload_box_id),
    )

    # Process the event and make sure an outbox event is published
    async with joint_fixture.kafka.record_events(
        in_topic=research_box_topic
    ) as recorder:
        await joint_fixture.event_subscriber.run(forever=False)
    assert recorder.recorded_events
    assert len(recorder.recorded_events) == 1
    assert recorder.recorded_events[0].payload["file_count"] == 1  # check one property

    # Query the box (should show updated file count and size)
    httpx_mock.add_response(
        method="GET",
        url=f"{access_url}/upload-access/users/{regular_user_id}/boxes/{box_id}",
        status_code=200,
    )
    updated_box = await orchestrator.get_research_data_upload_box(
        box_id=box_id,
        auth_context=user_auth_context,
    )
    assert updated_box.title == "Updated Test Box"
    assert updated_box.description == "Updated description"
    assert updated_box.version == 2
    assert updated_box.file_upload_box_version == 1
    assert updated_box.file_count == 1
    assert updated_box.size == 1024000

    # Set the state to LOCKED
    lock_request = UpdateUploadBoxRequest(version=updated_box.version, state="locked")
    httpx_mock.add_response(
        method="PATCH",
        url=f"{file_box_service_url}/boxes/{file_upload_box_id}",
        status_code=204,
    )
    await orchestrator.update_research_data_upload_box(
        box_id=box_id,
        request=lock_request,
        auth_context=user_auth_context,
    )

    # Verify the box is now locked
    box_after_lock = await orchestrator.get_research_data_upload_box(
        box_id=box_id,
        auth_context=user_auth_context,
    )
    assert box_after_lock.state == box_after_lock.file_upload_box_state == "locked"
    assert box_after_lock.version == 3

    # Submit accession map
    # Create test file IDs for files in the box
    file_id_1 = uuid4()
    file_id_2 = uuid4()
    file_id_3 = uuid4()

    # Mock the file box service to return the list of files
    httpx_mock.add_response(
        method="GET",
        url=f"{file_box_service_url}/boxes/{file_upload_box_id}/uploads",
        status_code=200,
        json=[
            {
                "id": str(file_id_1),
                "box_id": str(file_upload_box_id),
                "storage_alias": "test-storage",
                "bucket_id": "inbox",
                "alias": "file1.txt",
                "decrypted_sha256": "checksum1",
                "decrypted_size": 1000,
                "part_size": 100,
                "state": "awaiting_archival",
                "state_updated": now_utc_ms_prec().isoformat(),
            },
            {
                "id": str(file_id_2),
                "box_id": str(file_upload_box_id),
                "storage_alias": "test-storage",
                "bucket_id": "inbox",
                "alias": "file2.txt",
                "decrypted_sha256": "checksum2",
                "decrypted_size": 2000,
                "part_size": 100,
                "state": "awaiting_archival",
                "state_updated": now_utc_ms_prec().isoformat(),
            },
            {
                "id": str(file_id_3),
                "box_id": str(file_upload_box_id),
                "storage_alias": "test-storage",
                "bucket_id": "inbox",
                "alias": "file3.txt",
                "decrypted_sha256": "checksum3",
                "decrypted_size": 3000,
                "part_size": 100,
                "state": "awaiting_archival",
                "state_updated": now_utc_ms_prec().isoformat(),
            },
        ],
    )

    # Submit an accession map
    accession_map = AccessionMapRequest(
        version=box_after_lock.version,
        mapping={"GHGA001": file_id_1, "GHGA002": file_id_2, "GHGA003": file_id_3},
    )
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.accession_map_topic
    ) as accession_event_recorder:
        await orchestrator.update_accession_map(box_id=box_id, request=accession_map)

    # Verify the updated accession map was published
    assert accession_event_recorder.recorded_events
    assert len(accession_event_recorder.recorded_events) == 1
    accession_map_event = accession_event_recorder.recorded_events[0]
    assert accession_map_event.type_ == "upserted"
    assert accession_map_event.key == str(box_id)
    assert (
        accession_map_event.payload == accession_map.model_dump(mode="json")["mapping"]
    )

    # Make sure the RDUB version was bumped by the accession map update
    box_after_mapping = await orchestrator.get_research_data_upload_box(
        box_id=box_id,
        auth_context=user_auth_context,
    )
    assert box_after_mapping.version == 4

    # Mock the archive endpoint of the UCS
    httpx_mock.add_response(
        method="PATCH",
        url=f"{file_box_service_url}/boxes/{file_upload_box_id}",
        status_code=204,
    )

    # Archive the box via update
    archive_request = UpdateUploadBoxRequest(
        version=box_after_mapping.version, state="archived"
    )

    async with (
        joint_fixture.kafka.record_events(in_topic=audit_topic) as audit_event_recorder,
        joint_fixture.kafka.record_events(
            in_topic=research_box_topic
        ) as box_event_recorder,
    ):
        await orchestrator.update_research_data_upload_box(
            box_id=box_id,
            request=archive_request,
            auth_context=ds_auth_context,
        )

    # Verify audit and box events were published
    assert audit_event_recorder.recorded_events
    audit_event = audit_event_recorder.recorded_events[0]
    assert audit_event.payload["label"] == "ResearchDataUploadBox updated"
    assert box_event_recorder.recorded_events
    assert len(box_event_recorder.recorded_events) == 1
    assert box_event_recorder.recorded_events[0].payload["state"] == "archived"

    # Verify the box is now archived
    archived_box = await orchestrator.get_research_data_upload_box(
        box_id=box_id,
        auth_context=ds_auth_context,
    )
    assert archived_box.state == "archived"
    assert archived_box.file_upload_box_state == "archived"
    assert archived_box.version == box_after_mapping.version + 1
