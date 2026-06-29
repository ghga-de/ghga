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

"""Integration tests centered on the DlqManager class that use MongoDb and Kafka fixtures"""

from uuid import uuid4

import pytest
from hexkit.providers.mongodb.provider import document_to_dto
from hexkit.providers.mongodb.testutils import MongoDbFixture

from dlqs.models import StoredDLQEvent
from tests.fixtures import utils
from tests.fixtures.joint import JointFixture
from tests.fixtures.prepop import ReferenceEventsDict

pytestmark = pytest.mark.asyncio


async def test_discard(
    joint_fixture: JointFixture, mongodb: MongoDbFixture, prepopped_events
):
    """Verify that we can discard an event."""
    expected = prepopped_events[utils.UFS][utils.USER_EVENTS]
    assert len(expected) > 0

    db_name = joint_fixture.config.db_name
    db = mongodb.client[db_name]
    docs = db["dlqEvents"].find(
        {"dlq_info.service": utils.UFS, "topic": utils.USER_EVENTS}
    )
    observed = [
        document_to_dto(doc, id_field="dlq_id", dto_model=StoredDLQEvent)
        for doc in docs.to_list()
    ]
    observed.sort(key=lambda x: x.timestamp)
    assert observed == expected

    # Discard the event
    length_before_discard = len(observed)
    await joint_fixture.dlq_manager.discard_event(dlq_id=observed[0].dlq_id)

    # Manually get events again, convert to DTO, and sort by timestamp
    post_discard = (
        db["dlqEvents"]
        .find({"dlq_info.service": utils.UFS, "topic": utils.USER_EVENTS})
        .to_list()
    )
    post_discard = [
        document_to_dto(doc, id_field="dlq_id", dto_model=StoredDLQEvent)
        for doc in post_discard
    ]
    post_discard.sort(key=lambda x: x.timestamp)

    # Verify that the event that was discarded was the one with the oldest timestamp
    assert len(post_discard) == length_before_discard - 1
    assert post_discard == expected[1:]


async def test_discard_empty(joint_fixture: JointFixture, mongodb: MongoDbFixture):
    """Test for discarding an event when the database is empty"""
    # Verify that the database is empty
    db_name = joint_fixture.config.db_name
    db = mongodb.client[db_name]
    cursor = db["dlqEvents"].find()
    assert not cursor.to_list()

    # Discard an event with random non-existent dlq_id (nothing should happen)
    await joint_fixture.dlq_manager.discard_event(dlq_id=uuid4())


async def test_preview(joint_fixture: JointFixture, prepopped_events):
    """Test the preview functionality of the DLQ manager.

    Publishes events to the topic shared by the UFS and FSS services, then
    previews them. This test should cover:
    - Preview repeatability
    - Previewing events from different services and topics
    - Previewing events with different limits and skips
    """
    # Preview events and verify they match what was published
    expected = [
        StoredDLQEvent(**e.model_dump())
        for e in prepopped_events[utils.UFS][utils.USER_EVENTS]
    ]
    ufs_users_preview = await joint_fixture.dlq_manager.preview_events(
        service=utils.UFS, topic=utils.USER_EVENTS
    )
    assert ufs_users_preview == expected

    # Preview FSS user events with a limit of 1
    expected = [
        StoredDLQEvent(**e.model_dump())
        for e in prepopped_events[utils.FSS][utils.USER_EVENTS]
    ]
    fss_users_preview = await joint_fixture.dlq_manager.preview_events(
        service=utils.FSS,
        topic=utils.USER_EVENTS,
        limit=1,
    )
    assert len(fss_users_preview) == 1
    assert fss_users_preview[0] == expected[0]

    # Preview notifications with a skip of 8 and limit of 5 (return last 2 events)
    # The limit is an arbitrary non-zero amount that will include the last 2 events
    expected = [
        StoredDLQEvent(**e.model_dump())
        for e in prepopped_events[utils.UFS][utils.NOTIFICATIONS]
    ]
    notifications_preview = await joint_fixture.dlq_manager.preview_events(
        service=utils.UFS, topic=utils.NOTIFICATIONS, skip=8, limit=5
    )
    assert len(notifications_preview) == 2
    assert notifications_preview == expected[-2:]

    # Repeat last preview to verify repeatability
    notifications_preview2 = await joint_fixture.dlq_manager.preview_events(
        service=utils.UFS, topic=utils.NOTIFICATIONS, skip=8, limit=5
    )
    assert notifications_preview2 == notifications_preview


async def test_preview_with_various_skip_and_limit_args(
    joint_fixture: JointFixture, prepopped_events: ReferenceEventsDict
):
    """Another test to ensure preview_events returns the correct results

    This test mimics the scenario where two services subscribe to the same topic
    and both services encounter errors with a series of events from that topic.
    For both services we insert a number of events in the DB, which have the same
    timestamp and other information (except for the event ID).
    """
    # Test preview with different skip and limit values (all valid)
    pagination_params = [
        (0, None),
        (0, 5),
        (0, 25),
        (5, None),
        (5, 5),
        (5, 10),
        (5, 25),
    ]

    # Quick sanity check
    svc = utils.FSS
    topic = utils.USER_EVENTS
    assert svc in prepopped_events and topic in prepopped_events[svc]
    assert len(prepopped_events[utils.FSS][topic]) > 0

    # Preview the events using different valid parameters and compare to the reference
    for skip, limit in pagination_params:
        agg_op = joint_fixture.dlq_manager.preview_events(
            service=svc, topic=utils.USER_EVENTS, skip=skip, limit=limit
        )
        results = await agg_op
        end = skip + limit if limit else None
        expected = prepopped_events[svc][topic][skip:end]
        assert results == expected
