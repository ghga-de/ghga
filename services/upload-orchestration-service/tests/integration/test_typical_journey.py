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

"""Testing for listening to FileUploadBox events"""

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from ghga_event_schemas.pydantic_ import ResearchDataUploadBoxState
from ghga_service_commons.auth.ghga import AuthContext
from hexkit.utils import now_utc_ms_prec
from pytest_httpx import HTTPXMock

from tests.fixtures.joint import JointFixture
from uos.core.models import (
    UpdateUploadBoxRequest,
)

pytestmark = pytest.mark.asyncio()


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

    # 1. Creating a box (requires data steward)
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
        box_id = (
            await joint_fixture.upload_orchestrator.create_research_data_upload_box(
                title="Test Box",
                description="A test upload box",
                storage_alias="test-storage",
                data_steward_id=ds_user_id,
            )
        )
    assert audit_event_recorder.recorded_events
    audit_event = audit_event_recorder.recorded_events[0]
    assert audit_event.payload["label"] == "ResearchDataUploadBox created"  # suffices
    assert box_id is not None
    assert box_event_recorder.recorded_events
    assert len(box_event_recorder.recorded_events) == 1
    assert box_event_recorder.recorded_events[0].payload["id"] == str(box_id)

    # 2. Granting a user access to said box
    httpx_mock.add_response(
        method="POST",
        url=f"{access_url}/upload-access/users/{regular_user_id}/ivas/{iva_id}/boxes/{box_id}",
        status_code=200,
    )
    valid_from = now_utc_ms_prec()
    valid_until = now_utc_ms_prec() + timedelta(days=7)
    await joint_fixture.upload_orchestrator.grant_upload_access(
        user_id=regular_user_id,
        iva_id=iva_id,
        box_id=box_id,
        valid_from=valid_from,
        valid_until=valid_until,
        granting_user_id=ds_user_id,
    )

    # 3. Updating the title or description of the box by a DS
    update_request = UpdateUploadBoxRequest(
        title="Updated Test Box",
        description="Updated description",
    )
    async with (
        joint_fixture.kafka.record_events(in_topic=audit_topic) as audit_event_recorder,
        joint_fixture.kafka.record_events(
            in_topic=research_box_topic
        ) as box_event_recorder,
    ):
        await joint_fixture.upload_orchestrator.update_research_data_upload_box(
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

    # 4. Receiving a FileUploadBox update event from kafka (which belongs to the box)
    file_upload_box_event: dict[str, Any] = {
        "id": str(file_upload_box_id),
        "locked": False,
        "file_count": 3,
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
    assert recorder.recorded_events[0].payload["file_count"] == 3  # check one property

    # 5. Querying the box (should show updated file count and size)
    httpx_mock.add_response(
        method="GET",
        url=f"{access_url}/upload-access/users/{regular_user_id}/boxes/{box_id}",
        status_code=200,
    )
    updated_box = await joint_fixture.upload_orchestrator.get_research_data_upload_box(
        box_id=box_id,
        auth_context=user_auth_context,
    )
    assert updated_box.title == "Updated Test Box"
    assert updated_box.description == "Updated description"
    assert updated_box.file_count == 3
    assert updated_box.size == 1024000

    # 6. Setting the state to LOCKED
    lock_request = UpdateUploadBoxRequest(state=ResearchDataUploadBoxState.LOCKED)
    httpx_mock.add_response(
        method="PATCH",
        url=f"{file_box_service_url}/boxes/{file_upload_box_id}",
        status_code=204,
    )
    await joint_fixture.upload_orchestrator.update_research_data_upload_box(
        box_id=box_id,
        request=lock_request,
        auth_context=user_auth_context,
    )

    # Verify the box is now locked
    final_box = await joint_fixture.upload_orchestrator.get_research_data_upload_box(
        box_id=box_id,
        auth_context=user_auth_context,
    )
    assert final_box.state == ResearchDataUploadBoxState.LOCKED
