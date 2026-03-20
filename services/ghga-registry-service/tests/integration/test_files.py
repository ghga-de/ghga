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

"""Integration tests for the FileController and outbox events published by it"""

from uuid import uuid4

import pytest

from rs.adapters.inbound.fastapi_.rest_models import FileIdMappingRequest
from tests.fixtures import utils
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio


async def test_submission(joint_fixture: JointFixture):
    """Test the process starting from the start to finish.

    Submit a map to the HTTP API and inspect the outbox events.
    """
    study_pid = "test-study-1"
    accession1 = "GHGAF001"
    accession2 = "GHGAF002"
    file_id1 = uuid4()
    file_id2 = uuid4()
    mapping_request = FileIdMappingRequest(
        study_pid=study_pid, mapping={accession1: file_id1, accession2: file_id2}
    )

    # Prepare the HTTP request attributes
    body = mapping_request.model_dump(mode="json")
    url = f"/file-ids/{study_pid}"
    token_header = utils.map_file_ids_token_header(
        uos_jwk=joint_fixture.uos_jwk, study_pid=study_pid
    )

    # Submit the map to the endpoint and capture the events (Should be 2)
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.alt_accessions_topic
    ) as recorder:
        response = await joint_fixture.rest_client.post(
            url, json=body, headers=token_header
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
    assert event1.payload == {"accession": accession1, "file_id": str(file_id1)}
    assert event2.payload == {"accession": accession2, "file_id": str(file_id2)}
