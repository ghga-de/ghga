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

"""Tests for functionality related to the outbox subscriber."""

from unittest.mock import AsyncMock

import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from logot import Logot, logged

from tests_dcs.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()
CHANGE_EVENT_TYPE = "upserted"
DELETE_EVENT_TYPE = "deleted"

TEST_FILE_ID = "test_id"

TEST_FILE_DELETION_REQUESTED = event_schemas.FileDeletionRequested(file_id=TEST_FILE_ID)


async def test_outbox_subscriber_routing(joint_fixture: JointFixture):
    """Make sure the correct core method is called from the outbox subscriber."""
    await joint_fixture.kafka.publish_event(
        payload=TEST_FILE_DELETION_REQUESTED.model_dump(),
        type_=CHANGE_EVENT_TYPE,
        topic=joint_fixture.config.files_to_delete_topic,
        key=TEST_FILE_ID,
    )

    mock = AsyncMock()
    joint_fixture.data_repository.delete_file = mock

    await joint_fixture.outbox_subscriber.run(forever=False)
    mock.assert_awaited_once()


async def test_deletion_logs(joint_fixture: JointFixture, logot: Logot):
    """Test that the outbox subscriber logs deletions correctly.
    Consume a 'DELETED' event type for the outbox event.
    """
    # publish test event
    await joint_fixture.kafka.publish_event(
        payload=TEST_FILE_DELETION_REQUESTED.model_dump(),
        type_=DELETE_EVENT_TYPE,
        topic=joint_fixture.config.files_to_delete_topic,
        key=TEST_FILE_ID,
    )
    # consume that event
    await joint_fixture.outbox_subscriber.run(forever=False)

    # verify the log
    logot.assert_logged(
        logged.warning(
            "Received DELETED-type event for FileDeletionRequested"
            + f" with resource ID '{TEST_FILE_ID}'",
        )
    )
