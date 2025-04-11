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

"""Verify functionality related to the consumption of KafkaOutbox events."""

import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.dao import ResourceNotFoundError
from hexkit.providers.akafka.testutils import ExpectedEvent

from nos.core import notifications
from tests.conftest import TEST_USER
from tests.fixtures.joint import JointFixture

CHANGE_EVENT_TYPE = "upserted"
DELETE_EVENT_TYPE = "deleted"

pytestmark = pytest.mark.asyncio()


@pytest.mark.parametrize("user_id", ["test_id", "does_not_exist"])
async def test_user_data_deletion(joint_fixture: JointFixture, user_id: str):
    """Ensure that the `delete` function works correctly.

    The event should trigger the deletion of the user data via the orchestrator.
    The user_id 'test_id' should be found and deleted.
    The user_id 'does_not_exist' should not be found but also not raise an error.
    """
    # 1. Double check that the user data is found before running deletion.
    if user_id == "test_id":
        assert await joint_fixture.user_dao.get_by_id(user_id)

    # 2. Publish the event.
    await joint_fixture.kafka.publish_event(
        payload={},
        type_=DELETE_EVENT_TYPE,
        topic=joint_fixture.config.user_topic,
        key=user_id,
    )

    # 3. Run the outbox subscriber.
    await joint_fixture.event_subscriber.run(forever=False)

    # 4. Check that the user data is not found.
    with pytest.raises(ResourceNotFoundError):
        await joint_fixture.user_dao.get_by_id(user_id)


@pytest.mark.parametrize(
    "user",
    [
        TEST_USER.model_copy(
            update={
                "name": "new name",
                "academic_title": event_schemas.AcademicTitle.PROF,
                "email": "modified@test.com",
            }
        ),
        event_schemas.User(
            user_id="new_user", name="new user", email="new_user@xyz.com"
        ),
    ],
    ids=["modified user", "new user"],
)
async def test_user_data_upsert(
    joint_fixture: JointFixture,
    user: event_schemas.User,
):
    """Ensure that the `upsert` function works correctly.

    The 'upserted' event should trigger the upsertion of the user data via the
    orchestrator. This does not test for resulting notifications, only upsertion.
    """
    # Check that the user is found if it's the test user, otherwise not.
    if user.user_id == TEST_USER.user_id:
        assert await joint_fixture.user_dao.get_by_id(user.user_id)
    else:
        with pytest.raises(ResourceNotFoundError):
            assert await joint_fixture.user_dao.get_by_id(user.user_id)

    # Publish the change event.
    await joint_fixture.kafka.publish_event(
        payload=user.model_dump(),
        type_=CHANGE_EVENT_TYPE,
        topic=joint_fixture.config.user_topic,
        key=user.user_id,
    )

    # Run the outbox subscriber.
    await joint_fixture.event_subscriber.run(forever=False)

    # Check that the user data is found.
    result = await joint_fixture.user_dao.get_by_id(user.user_id)
    assert result == user


@pytest.mark.parametrize(
    "changed_details",
    [
        {"name": "new name"},
        {"email": "different@example.com"},
        {"name": "another name", "email": "anders@example.com"},
        {},
        {"title": event_schemas.AcademicTitle.PROF},
    ],
    ids=["name", "email", "both", "neither", "title"],
)
async def test_user_reregistration_notifications(
    joint_fixture: JointFixture,
    changed_details: dict[str, str],
):
    """Test that upsertion emits the expected notifications.

    When a name changes, ensure the new name is used.
    When an email changes, ensure the old email is used.
    When neither changes, ensure no notification is emitted.
    """
    user = TEST_USER.model_copy(update=changed_details)

    # Publish the change event.
    await joint_fixture.kafka.publish_event(
        payload=user.model_dump(),
        type_=CHANGE_EVENT_TYPE,
        topic=joint_fixture.config.user_topic,
        key=user.user_id,
    )

    # Prepare the expected notification.
    expected_notifications = []
    if "name" in changed_details or "email" in changed_details:
        expected_notifications.append(
            event_schemas.Notification(
                recipient_email=TEST_USER.email
                if "email" in changed_details
                else user.email,
                subject="Account Details Changed",
                recipient_name=user.name,
                plaintext_body=notifications.USER_REREGISTERED_TO_USER.text.format(
                    changed_details=" and ".join(sorted(changed_details.keys())),
                    helpdesk_email=joint_fixture.config.helpdesk_email,
                ),
            )
        )

    # Compile expected events list
    topic = joint_fixture.config.notification_topic
    expected_events = [
        ExpectedEvent(
            type_=joint_fixture.config.notification_type,
            payload=notification.model_dump(),
            key=notification.recipient_email,
        )
        for notification in expected_notifications
    ]

    # Run the outbox subscriber and check that the expected notifications were emitted.
    async with joint_fixture.kafka.expect_events(expected_events, in_topic=topic):
        await joint_fixture.event_subscriber.run(forever=False)
