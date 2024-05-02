# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""Tests typical user journeys"""

import json

import pytest
from fastapi import status
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.akafka.testutils import ExpectedEvent
from httpx import Headers

from tests_pcs.fixtures.joint import (  # noqa: F401
    JointFixture,
    joint_fixture,
    kafka_fixture,
)


@pytest.mark.asyncio
async def test_journey(joint_fixture: JointFixture):  # noqa: F811
    """Simulates a typical, successful API journey."""
    file_id = "test_id"

    files_deletion_event = event_schemas.FileDeletionRequested(file_id=file_id)
    async with joint_fixture.kafka.expect_events(
        events=[
            ExpectedEvent(
                payload=json.loads(files_deletion_event.model_dump_json()),
                type_=joint_fixture.config.files_to_delete_type,
            )
        ],
        in_topic=joint_fixture.config.files_to_delete_topic,
    ):
        headers = Headers({"Authorization": f"Bearer {joint_fixture.token}"})
        response = await joint_fixture.rest_client.delete(
            f"/files/{file_id}", headers=headers, timeout=5
        )

    assert response.status_code == status.HTTP_202_ACCEPTED

    headers = Headers({"Authorization": "Bearer not-a-valid-token"})
    response = await joint_fixture.rest_client.delete(
        f"/files/{file_id}", headers=headers, timeout=5
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
