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
"""Tests for event sub/pub"""

from typing import Any

import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.akafka.testutils import ExpectedEvent
from logot import Logot, logged

from nos.core import notifications
from tests.conftest import TEST_USER
from tests.fixtures.joint import JointFixture

DATASET_ID = "dataset1"
pytestmark = pytest.mark.asyncio()


def access_request_payload(user_id: str) -> dict[str, Any]:
    """Succinctly create the payload for an access request event."""
    return event_schemas.AccessRequestDetails(
        user_id=user_id, dataset_id=DATASET_ID
    ).model_dump()


def iva_state_payload(user_id: str, state: event_schemas.IvaState) -> dict[str, Any]:
    """Succinctly create the payload for an IVA state change event."""
    return event_schemas.UserIvaState(
        user_id=user_id,
        state=state,
        value=None,
        type=None,
    ).model_dump()


@pytest.mark.parametrize(
    "user_notification_content, user_kwargs, ds_notification_content, ds_kwargs, event_type",
    [
        (  # Test access request created
            notifications.ACCESS_REQUEST_CREATED_TO_USER,
            {"dataset_id": DATASET_ID},
            notifications.ACCESS_REQUEST_CREATED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "email": TEST_USER.email,
                "dataset_id": DATASET_ID,
            },
            "created",
        ),
        (  # Test access request allowed
            notifications.ACCESS_REQUEST_ALLOWED_TO_USER,
            {"dataset_id": DATASET_ID},
            notifications.ACCESS_REQUEST_ALLOWED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "dataset_id": DATASET_ID,
            },
            "allowed",
        ),
        (  # Test access request denied
            notifications.ACCESS_REQUEST_DENIED_TO_USER,
            {"dataset_id": DATASET_ID},
            notifications.ACCESS_REQUEST_DENIED_TO_DS,
            {
                "full_user_name": TEST_USER.name,
                "dataset_id": DATASET_ID,
            },
            "denied",
        ),
    ],
)
async def test_access_request(
    joint_fixture: JointFixture,
    user_notification_content: notifications.Notification,
    user_kwargs: dict[str, Any],
    ds_notification_content: notifications.Notification,
    ds_kwargs: dict[str, Any],
    event_type: str,
):
    """Test that the access request created event is processed correctly.

    Test will also check idempotence.
    """
    test_user = await joint_fixture.user_dao.get_by_id(TEST_USER.user_id)

    event_type_to_use = getattr(
        joint_fixture.config, f"access_request_{event_type}_event_type"
    )

    assert event_type_to_use

    user_notification = event_schemas.Notification(
        recipient_email=test_user.email,
        subject=user_notification_content.subject,
        recipient_name=test_user.name,
        plaintext_body=user_notification_content.text.format(**user_kwargs),
    )

    data_steward_notification = event_schemas.Notification(
        recipient_email=joint_fixture.config.central_data_stewardship_email,
        subject=ds_notification_content.subject,
        recipient_name="Data Steward",
        plaintext_body=ds_notification_content.text.format(**ds_kwargs),
    )

    expected = [
        ExpectedEvent(
            payload=user_notification.model_dump(),
            type_=joint_fixture.config.notification_event_type,
            key=test_user.email,
        ),
        ExpectedEvent(
            payload=data_steward_notification.model_dump(),
            type_=joint_fixture.config.notification_event_type,
            key=joint_fixture.config.central_data_stewardship_email,
        ),
    ]

    # Create the kafka event that would be published by the access request service
    await joint_fixture.kafka.publish_event(
        payload=access_request_payload(test_user.user_id),
        type_=event_type_to_use,
        topic=joint_fixture.config.access_request_events_topic,
    )

    # Consume the event, triggering the generation of two notifications
    async with joint_fixture.kafka.expect_events(
        events=expected,
        in_topic=joint_fixture.config.notification_event_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)

    # Publish and consume event again to check idempotence
    await joint_fixture.kafka.publish_event(
        payload=access_request_payload(test_user.user_id),
        type_=event_type_to_use,
        topic=joint_fixture.config.access_request_events_topic,
    )

    async with joint_fixture.kafka.expect_events(
        events=expected,
        in_topic=joint_fixture.config.notification_event_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)


async def test_missing_user_id_access_requests(
    joint_fixture: JointFixture, logot: Logot
):
    """Test for error handling in case of invalid user id, specifically for the access
    request events.
    """
    payload = access_request_payload("bogus_user_id")

    event_types = (
        joint_fixture.config.access_request_created_event_type,
        joint_fixture.config.access_request_allowed_event_type,
        joint_fixture.config.access_request_denied_event_type,
    )

    for event_type in event_types:
        await joint_fixture.kafka.publish_event(
            payload=payload,
            type_=event_type,
            topic=joint_fixture.config.access_request_events_topic,
        )

        with pytest.raises(joint_fixture.orchestrator.MissingUserError):
            await joint_fixture.event_subscriber.run(forever=False)
        logot.assert_logged(
            logged.error(
                "Unable to publish %s notification as user ID %s was not found in"
                + " the database."
            )
        )


async def test_missing_user_id_iva_state_changes(
    joint_fixture: JointFixture, logot: Logot
):
    """Test for error handling in case of invalid user id, specifically for the IVA
    state change events.
    """
    payloads = (
        iva_state_payload("bogus_user_id", event_schemas.IvaState.CODE_REQUESTED),
        iva_state_payload("bogus_user_id", event_schemas.IvaState.CODE_TRANSMITTED),
        iva_state_payload("bogus_user_id", event_schemas.IvaState.VERIFIED),
        iva_state_payload("bogus_user_id", event_schemas.IvaState.UNVERIFIED),
    )

    event_types = (
        joint_fixture.config.iva_state_changed_event_type,  # requested
        joint_fixture.config.iva_state_changed_event_type,  # transmitted
        joint_fixture.config.iva_state_changed_event_type,  # verified
        joint_fixture.config.iva_state_changed_event_type,  # unverified
    )
    for payload, event_type in zip(payloads, event_types, strict=True):
        await joint_fixture.kafka.publish_event(
            payload=payload,
            type_=event_type,
            topic=joint_fixture.config.access_request_events_topic,
        )

        with pytest.raises(joint_fixture.orchestrator.MissingUserError):
            await joint_fixture.event_subscriber.run(forever=False)
        logot.assert_logged(
            logged.error(
                "Unable to publish %s notification as user ID %s was not found in"
                + " the database."
            )
        )


async def test_file_registered(joint_fixture: JointFixture):
    """Test that the file registered events are translated into a notification."""
    # Prepare triggering event (the file registration event).
    # The only thing we care about is the file_id, so the rest can be blank.
    trigger_event = event_schemas.FileInternallyRegistered(
        upload_date=now_as_utc().isoformat(),
        file_id=DATASET_ID,
        object_id="",
        bucket_id="",
        s3_endpoint_alias="",
        decrypted_size=0,
        decryption_secret_id="",
        content_offset=0,
        encrypted_part_size=0,
        encrypted_parts_md5=[""],
        encrypted_parts_sha256=[""],
        decrypted_sha256="",
    )

    # Publish the trigger event
    await joint_fixture.kafka.publish_event(
        payload=trigger_event.model_dump(),
        type_=joint_fixture.config.file_registered_event_type,
        topic=joint_fixture.config.file_registered_event_topic,
    )

    # Define the event that should be published by the NOS when the trigger is consumed
    expected_notification = event_schemas.Notification(
        recipient_email=joint_fixture.config.central_data_stewardship_email,
        recipient_name="Data Steward",
        subject="File upload completed",
        plaintext_body=f"The file {DATASET_ID} has been successfully uploaded.",
    )

    expected_event = ExpectedEvent(
        payload=expected_notification.model_dump(),
        type_=joint_fixture.config.notification_event_type,
        key=joint_fixture.config.central_data_stewardship_email,
    )

    # consume the event and verify that the expected event is published
    async with joint_fixture.kafka.expect_events(
        events=[expected_event],
        in_topic=joint_fixture.config.notification_event_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)


@pytest.mark.parametrize(
    "iva_state,expected_user_notification,expected_ds_notification",
    [
        (
            event_schemas.IvaState.CODE_REQUESTED,
            notifications.IVA_CODE_REQUESTED_TO_USER,
            notifications.IVA_CODE_REQUESTED_TO_DS,
        ),
        (
            event_schemas.IvaState.CODE_TRANSMITTED,
            notifications.IVA_CODE_TRANSMITTED_TO_USER,
            None,
        ),
        (
            event_schemas.IvaState.VERIFIED,
            None,
            notifications.IVA_CODE_SUBMITTED_TO_DS,
        ),
        (
            event_schemas.IvaState.UNVERIFIED,
            None,
            notifications.IVA_UNVERIFIED_TO_DS,
        ),
    ],
)
async def test_iva_state_change(
    joint_fixture: JointFixture,
    iva_state: event_schemas.IvaState,
    expected_user_notification: notifications.Notification | None,
    expected_ds_notification: notifications.Notification | None,
):
    """Test that the IVA state change events are translated into the proper notification.

    This does not check the wording or content of the notifications, only that the
    correct notifications are generated for each state change.
    """
    # Prepare triggering event (the IVA state change event).
    trigger_event = event_schemas.UserIvaState(
        user_id=TEST_USER.user_id,
        state=iva_state,
        value=None,
        type=event_schemas.IvaType.FAX,
    )

    # Publish the trigger event
    await joint_fixture.kafka.publish_event(
        payload=trigger_event.model_dump(),
        type_=joint_fixture.config.iva_state_changed_event_type,
        topic=joint_fixture.config.iva_state_changed_event_topic,
        key=TEST_USER.user_id,
    )

    # Build a notification payload for the user, if applicable
    user_notification = (
        event_schemas.Notification(
            recipient_email=TEST_USER.email,
            subject=expected_user_notification.subject,
            recipient_name=TEST_USER.name,
            plaintext_body=expected_user_notification.text,
        )
        if expected_user_notification
        else None
    )

    # Build a notification payload for the data steward, if applicable
    data_steward_notification = (
        event_schemas.Notification(
            recipient_email=joint_fixture.config.central_data_stewardship_email,
            subject=expected_ds_notification.subject,
            recipient_name="Data Steward",
            plaintext_body=expected_ds_notification.text.format(
                full_user_name=TEST_USER.name,
                email=TEST_USER.email,
                type=trigger_event.type,
            ),
        )
        if expected_ds_notification
        else None
    )

    # Combine the two notifications into a list of expected events
    expected_events = []
    for notification in [user_notification, data_steward_notification]:
        if notification:
            expected_events.append(
                ExpectedEvent(
                    payload=notification.model_dump(),
                    type_=joint_fixture.config.notification_event_type,
                )
            )

    # Consume the event and verify that the expected events are published
    async with joint_fixture.kafka.expect_events(
        events=expected_events,
        in_topic=joint_fixture.config.notification_event_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)


async def test_all_ivas_reset(joint_fixture: JointFixture):
    """Test that the 'all IVA invalidated' events are translated into a notification."""
    # Prepare triggering event (the IVA state change event).
    trigger_event = event_schemas.UserIvaState(
        user_id=TEST_USER.user_id,
        state=event_schemas.IvaState.UNVERIFIED,
        value=None,
        type=None,
    )

    # Publish the trigger event
    await joint_fixture.kafka.publish_event(
        payload=trigger_event.model_dump(),
        type_=joint_fixture.config.iva_state_changed_event_type,
        topic=joint_fixture.config.iva_state_changed_event_topic,
        key=f"all-{TEST_USER.user_id}",
    )

    # Define the event that should be published by the NOS when the trigger is consumed
    ds_email = joint_fixture.config.central_data_stewardship_email
    expected_notification = event_schemas.Notification(
        recipient_email=TEST_USER.email,
        recipient_name=TEST_USER.name,
        subject="Contact Address Invalidation",
        plaintext_body=f"""
All of your registered contact addresses now need re-verification due to the establishment
of a new 2nd authentication factor.

If you have any questions, please contact a Data Steward at GHGA: {ds_email}.
""",
    )

    expected_event = ExpectedEvent(
        payload=expected_notification.model_dump(),
        type_=joint_fixture.config.notification_event_type,
    )

    # consume the event and verify that the expected event is published
    async with joint_fixture.kafka.expect_events(
        events=[expected_event],
        in_topic=joint_fixture.config.notification_event_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)


async def test_second_factor_recreated_notification(joint_fixture: JointFixture):
    """Test that the second factor recreated event is translated into a notification."""
    # Prepare triggering event (the second factor recreated event).
    payload = event_schemas.UserID(
        user_id=TEST_USER.user_id,
    )

    # Publish the trigger event
    await joint_fixture.kafka.publish_event(
        payload=payload.model_dump(),
        type_=joint_fixture.config.second_factor_recreated_event_type,
        topic=joint_fixture.config.second_factor_recreated_event_topic,
        key=TEST_USER.user_id,
    )

    # Define the event that should be published by the NOS when the trigger is consumed
    expected_notification_content = (
        notifications.SECOND_FACTOR_RECREATED_TO_USER.formatted(
            support_email=joint_fixture.config.central_data_stewardship_email
        )
    )

    expected_notification = event_schemas.Notification(
        recipient_email=TEST_USER.email,
        recipient_name=TEST_USER.name,
        subject=expected_notification_content.subject,
        plaintext_body=expected_notification_content.text,
    )

    expected_event = ExpectedEvent(
        payload=expected_notification.model_dump(),
        type_=joint_fixture.config.notification_event_type,
    )

    # consume the event and verify that the expected event is published
    async with joint_fixture.kafka.expect_events(
        events=[expected_event],
        in_topic=joint_fixture.config.notification_event_topic,
    ):
        await joint_fixture.event_subscriber.run(forever=False)
