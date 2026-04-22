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

"""Integration tests for the REST API with real infrastructure components"""

from uuid import uuid4

import pytest
from hexkit.utils import now_utc_ms_prec
from pytest_httpx import HTTPXMock

from rs.core.models import (
    AccessionMapRequest,
    FileUploadWithAccession,
)
from tests.fixtures import utils
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio


async def test_submission(
    joint_fixture: JointFixture, httpx_mock: HTTPXMock, ds_auth_headers
):
    """Test the process starting from the start to finish.

    Submit a map to the HTTP API and inspect the outbox events.
    """
    accession1 = "GHGAF001"
    accession2 = "GHGAF002"
    file_id1 = uuid4()
    file_id2 = uuid4()
    file_upload_box_id = uuid4()

    # Mock the UCS call to create a FileUploadBox (occurs when we create an RDUB)
    httpx_mock.add_response(
        method="POST",
        url=f"{joint_fixture.config.ucs_url}/boxes",
        status_code=201,
        json=str(file_upload_box_id),
    )

    # Create an RDUB
    rdub_manager = joint_fixture.ghga_registry.rdub_manager
    box_id = await rdub_manager.create_research_data_upload_box(
        title="Box A",
        description="Description of Box A",
        storage_alias="HD01",
        data_steward_id=utils.TEST_DS_ID,
    )

    # Mock the UCS call to list files in the FileUploadBox
    file_upload1 = FileUploadWithAccession(
        id=file_id1,
        box_id=box_id,
        storage_alias="HD01",
        bucket_id="inbox",
        object_id=uuid4(),
        alias="test1.bam",
        decrypted_sha256="checksum1",
        decrypted_size=10 * 1024**3,
        encrypted_size=10 * 1024**3 + 124,
        part_size=100,
        state="archived",
        state_updated=now_utc_ms_prec(),
        accession=accession1,
    )
    file_upload2 = file_upload1.model_copy(
        update={"id": file_id2, "alias": "test2.bam", "accession": accession2}
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{joint_fixture.config.ucs_url}/boxes/{file_upload_box_id}/uploads",
        status_code=200,
        json=[
            file_upload1.model_dump(mode="json"),
            file_upload2.model_dump(mode="json"),
        ],
    )

    # Prepare the HTTP request attributes
    mapping_request = AccessionMapRequest(
        box_version=0,
        study_id="test-study-1",
        mapping={accession1: file_id1, accession2: file_id2},
    )
    body = mapping_request.model_dump(mode="json")
    url = f"/upload-boxes/{box_id}/file-ids"

    # Submit the map to the endpoint and capture the events (Should be 2)
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.accession_map_topic
    ) as recorder:
        response = await joint_fixture.rest_client.post(
            url, json=body, headers=ds_auth_headers
        )
        assert response.status_code == 204

    # Sort the events (should already be in order, but no reason not to make sure)
    assert len(recorder.recorded_events or []) == 2
    event1, event2 = sorted(
        recorder.recorded_events, key=lambda x: str(x.payload["accession"])
    )

    # Inspect the events. Check the type, key, and payload
    assert event1.type_ == event2.type_ == "upserted"
    assert event1.key == accession1
    assert event2.key == accession2
    assert event1.payload["accession"] == accession1
    assert event1.payload["file_id"] == str(file_id1)
    assert event2.payload["accession"] == accession2
    assert event2.payload["file_id"] == str(file_id2)
