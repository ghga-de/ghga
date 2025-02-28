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
#

"""Tests typical user journeys"""

import json
from typing import Literal

import pytest
from fastapi import status
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.correlation import new_correlation_id, set_correlation_id
from hexkit.protocols.dao import ResourceNotFoundError
from hexkit.providers.akafka.testutils import ExpectedEvent
from httpx import Headers

from tests_pcs.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()


TEST_FILE_ID = "test_id"


def expected_event_from_file_id(
    type_: Literal["upserted", "deleted"], file_id: str
) -> ExpectedEvent:
    """Given a file ID and event type, return a FileDeletionRequest formatted
    as an ExpectedEvent.
    """
    payload = {}
    if type_ == "upserted":
        files_deletion_event = event_schemas.FileDeletionRequested(file_id=TEST_FILE_ID)
        payload = json.loads(files_deletion_event.model_dump_json())
    expected_event = ExpectedEvent(payload=payload, type_=type_, key=file_id)
    return expected_event


async def test_happy_journey(joint_fixture: JointFixture):
    """Simulates a typical, successful API journey.

    A file ID is sent to the deletion request API endpoint, which ultimately results in
    a the supplied ID being saved in the database as well as emitted via an event.
    """
    expected_event = expected_event_from_file_id("upserted", TEST_FILE_ID)

    async with joint_fixture.kafka.expect_events(
        events=[expected_event],
        in_topic=joint_fixture.config.file_deletion_request_topic,
    ):
        headers = Headers({"Authorization": f"Bearer {joint_fixture.token}"})
        response = await joint_fixture.rest_client.delete(
            f"/files/{TEST_FILE_ID}", headers=headers, timeout=5
        )

    assert response.status_code == status.HTTP_202_ACCEPTED


async def test_unauthorized_request(joint_fixture: JointFixture):
    """Ensure that an unauthorized request to the deletion request API endpoint fails."""
    headers = Headers({"Authorization": "Bearer not-a-valid-token"})
    response = await joint_fixture.rest_client.delete(
        f"/files/{TEST_FILE_ID}", headers=headers, timeout=5
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_dto_deletion(joint_fixture: JointFixture):
    """Ensure that the correct outbox event is published for deletion of a deletion
    request from the database -- even though this is not part of the typical request flow.
    """
    # Throw an error if test cleanup isn't working
    with pytest.raises(ResourceNotFoundError):
        await joint_fixture.dao.get_by_id(TEST_FILE_ID)

    correlation_id = new_correlation_id()
    async with set_correlation_id(correlation_id):
        # insert event and consume the resulting upsertion event
        expected_upsertion = expected_event_from_file_id("upserted", TEST_FILE_ID)
        async with joint_fixture.kafka.expect_events(
            events=[expected_upsertion],
            in_topic=joint_fixture.config.file_deletion_request_topic,
        ):
            await joint_fixture.dao.insert(
                event_schemas.FileDeletionRequested(file_id=TEST_FILE_ID)
            )

        # delete and consume the resulting deletion event
        expected_deletion = expected_event_from_file_id(
            type_="deleted", file_id=TEST_FILE_ID
        )
        async with joint_fixture.kafka.expect_events(
            events=[expected_deletion],
            in_topic=joint_fixture.config.file_deletion_request_topic,
        ):
            await joint_fixture.dao.delete(TEST_FILE_ID)
