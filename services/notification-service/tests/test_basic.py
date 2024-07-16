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

"""Test basic event consumption"""

from hashlib import sha256
from typing import cast

import pytest

from ns.adapters.outbound.smtp_client import SmtpClient
from ns.core.models import NotificationRecord
from ns.core.notifier import Notifier
from tests.fixtures.joint import JointFixture
from tests.fixtures.server import DummyServer
from tests.fixtures.utils import make_notification

pytestmark = pytest.mark.asyncio()

sample_notification = {
    "recipient_email": "test@example.com",
    "email_cc": ["test2@test.com", "test3@test.com"],
    "email_bcc": ["test4@test.com", "test5@test.com"],
    "subject": "Test123",
    "recipient_name": "Yolanda Martinez",
    "plaintext_body": "Where are you, where are you, Yolanda?",
}


@pytest.mark.parametrize(
    "notification_details",
    [sample_notification],
)
async def test_email_construction(
    joint_fixture: JointFixture,
    notification_details,
):
    """Verify that the email is getting constructed properly from the template."""
    # Cast notifier type
    joint_fixture.notifier = cast(Notifier, joint_fixture.notifier)

    notification = make_notification(notification_details)

    msg = joint_fixture.notifier._construct_email(notification=notification)

    assert msg is not None

    plaintext_body = msg.get_body(preferencelist="plain")
    assert plaintext_body is not None

    plaintext_content = plaintext_body.get_content()  # type: ignore
    expected_plaintext = (
        "Dear Yolanda Martinez,\n\nWhere are you, where are you, Yolanda?\n"
        + "\nWarm regards,\n\nThe GHGA Team"
    )
    assert plaintext_content.strip() == expected_plaintext

    html_body = msg.get_body(preferencelist="html")
    assert html_body is not None

    html_content = html_body.get_content()  # type: ignore
    assert html_content is not None

    expected_html = (
        '<!DOCTYPE html><html><head></head><body style="color: #00393f;'
        + 'padding: 12px;"><h2>Dear Yolanda Martinez,</h2><p>Where are you,'
        + " where are you, Yolanda?</p><p>Warm regards,</p><h3>The GHGA Team</h3>"
        + "</body></html>"
    )
    assert html_content.strip() == expected_html


async def test_failed_authentication(joint_fixture: JointFixture):
    """Change login credentials so authentication fails."""
    # Cast notifier type
    joint_fixture.notifier = cast(Notifier, joint_fixture.notifier)

    server = DummyServer(config=joint_fixture.config)

    # change the login credentials so that the authentication fails
    server.login = "bob@bobswebsite.com"
    server.password = "notCorrect"
    notification = make_notification(sample_notification)

    expected_email = joint_fixture.notifier._construct_email(
        notification=notification,
    )

    # send the notification so it gets intercepted by the dummy client
    with pytest.raises(SmtpClient.FailedLoginError):
        async with server.expect_email(expected_email=expected_email):
            await joint_fixture.notifier.send_notification(notification=notification)

    # verify that the email is in the database but not marked as sent
    expected_record = joint_fixture.notifier._create_notification_record(
        notification=notification
    )

    record_in_db = await joint_fixture.notifier._notification_record_dao.get_by_id(
        id_=expected_record.hash_sum
    )

    assert not record_in_db.sent


async def test_consume_thru_send(joint_fixture: JointFixture):
    """Verify that the event is correctly translated into a basic email object"""
    await joint_fixture.kafka.publish_event(
        payload={
            "recipient_email": "test@example.com",
            "email_cc": [],
            "email_bcc": [],
            "subject": "Test123",
            "recipient_name": "Yolanda Martinez",
            "plaintext_body": "Where are you, where are you, Yolanda?",
        },
        type_=joint_fixture.config.notification_event_type,
        topic=joint_fixture.config.notification_event_topic,
    )

    with pytest.raises(ConnectionRefusedError):
        # the connection error tells us that the smtp_client tried to connect, which
        # means that the consumer successfully passed the event through the notifier
        # and on to the client for emailing.
        await joint_fixture.event_subscriber.run(forever=False)


async def test_helper_functions(joint_fixture: JointFixture):
    """Unit test for the _has_been_sent function, _create_notification_record,
    and _register_new_notification function.
    """
    # Cast notifier type
    joint_fixture.notifier = cast(Notifier, joint_fixture.notifier)

    # first, create a notification
    notification = make_notification(sample_notification)

    # manually create a NotificationRecord for the notification
    expected_record = NotificationRecord(
        hash_sum=sha256(notification.model_dump_json().encode("utf-8")).hexdigest(),
        sent=False,
    )

    # Now create the record using the notifier's function and compare
    actual_record = joint_fixture.notifier._create_notification_record(
        notification=notification
    )

    assert actual_record.model_dump() == expected_record.model_dump()

    # Now check the _has_been_sent function before the record has been inserted
    assert not await joint_fixture.notifier._has_been_sent(
        hash_sum=actual_record.hash_sum
    )

    # register the notification
    await joint_fixture.notifier._register_new_notification(
        notification_record=actual_record
    )

    # Verify the record is in the database
    record_in_db = await joint_fixture.notifier._notification_record_dao.get_by_id(
        id_=actual_record.hash_sum
    )

    # Extra sanity check to make sure they're the same
    assert record_in_db.model_dump() == actual_record.model_dump()

    # Record still has not been sent, but now it's in the database. Do another check
    assert not await joint_fixture.notifier._has_been_sent(
        hash_sum=actual_record.hash_sum
    )

    # Now mark the record as sent
    actual_record.sent = True
    await joint_fixture.notifier._notification_record_dao.update(dto=actual_record)

    # Now the record has been marked as sent, so _has_been_sent should return False
    assert await joint_fixture.notifier._has_been_sent(hash_sum=actual_record.hash_sum)


async def test_idempotence_and_transmission(joint_fixture: JointFixture):
    """Consume identical events and verify that only one email is sent."""
    # Cast notifier type
    joint_fixture.notifier = cast(Notifier, joint_fixture.notifier)

    notification_event = make_notification(sample_notification)
    await joint_fixture.kafka.publish_event(
        payload=notification_event.model_dump(),
        type_=joint_fixture.config.notification_event_type,
        topic=joint_fixture.config.notification_event_topic,
    )

    # generate the hash sum for the notification
    record = joint_fixture.notifier._create_notification_record(
        notification=notification_event
    )

    # the record hasn't been sent, so this should return False
    assert not await joint_fixture.notifier._has_been_sent(hash_sum=record.hash_sum)

    server = DummyServer(config=joint_fixture.config)
    expected_email = joint_fixture.notifier._construct_email(
        notification=notification_event,
    )

    # Intercept the email with a dummy server and check content upon receipt
    async with server.expect_email(expected_email=expected_email):
        # consume the event to send the notification email to the dummy server
        await joint_fixture.event_subscriber.run(forever=False)

    # Verify that the notification has now been marked as sent
    assert await joint_fixture.notifier._has_been_sent(hash_sum=record.hash_sum)

    # Now publish the same event again
    await joint_fixture.kafka.publish_event(
        payload=notification_event.model_dump(),
        type_=joint_fixture.config.notification_event_type,
        topic=joint_fixture.config.notification_event_topic,
    )

    # Consume the event, which should NOT send anything and create no ConnectionError
    # For clarification for anyone visiting this after a while, the ConnectionError
    # would be raised if it tried to connect to an actual server because the config
    # is bogus. If no ConnectionError is raised, that means the Notifier didn't try
    # to send an email.
    await joint_fixture.event_subscriber.run(forever=False)
