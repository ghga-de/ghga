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

"""Test basic event consumption"""

import html
import json
import smtplib
from contextlib import contextmanager
from email.message import EmailMessage
from hashlib import sha256
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from hexkit.correlation import correlation_id_var
from hexkit.protocols.dao import ResourceNotFoundError
from pydantic import SecretStr

from ns.adapters.outbound.smtp_client import (
    SmtpAuthConfig,
    SmtpClient,
    SmtpClientConfig,
)
from ns.core.models import NotificationRecord
from ns.core.notifier import Notifier
from tests.fixtures.config import get_config
from tests.fixtures.joint import JointFixture
from tests.fixtures.server import DummyServer
from tests.fixtures.utils import make_notification

pytestmark = pytest.mark.asyncio()

TEST_CORRELATION_ID = "6914c8cd-1f18-43da-ac6c-c43cca3f36cc"

sample_notification = {
    "recipient_email": "test@example.com",
    "email_cc": ["test2@test.com", "test3@test.com"],
    "email_bcc": ["test4@test.com", "test5@test.com"],
    "subject": "Test123",
    "recipient_name": "Yolanda Martinez",
    "plaintext_body": "Where are you, where are you, Yolanda?",
}


@pytest.fixture(autouse=True)
def correlation_id_fixture():
    """Provides a new correlation ID for each test case."""
    # we cannot use an async fixture with set_correlation_id(),
    # because it would run in a different context from the test
    token = correlation_id_var.set(TEST_CORRELATION_ID)
    yield
    correlation_id_var.reset(token)


@pytest.mark.parametrize("notification_details", [sample_notification])
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

    plaintext_content = plaintext_body.get_content()
    expected_plaintext = (
        "Dear Yolanda Martinez,\n\nWhere are you, where are you, Yolanda?\n"
        + "\nWarm regards,\n\nThe GHGA Team"
    )
    assert plaintext_content.strip() == expected_plaintext

    html_body = msg.get_body(preferencelist="html")
    assert html_body is not None

    html_content = html_body.get_content()
    assert html_content is not None

    expected_html = (
        '<!DOCTYPE html><html><head></head><body style="color: #00393f;'
        + 'padding: 12px;"><h2>Dear Yolanda Martinez,</h2><p>Where are you,'
        + " where are you, Yolanda?</p><p>Warm regards,</p><h3>The GHGA Team</h3>"
        + "</body></html>"
    )
    assert html_content.strip() == expected_html


async def test_bad_login_config():
    """Verify that we get an error if credentials are misconfigured"""
    with pytest.raises(ValueError):
        SmtpClientConfig(
            smtp_host="127.0.0.1",
            smtp_port=587,
            smtp_auth=SmtpAuthConfig(username="test", password=None),  # type: ignore
        )

    with pytest.raises(ValueError):
        SmtpClientConfig(
            smtp_host="127.0.0.1",
            smtp_port=587,
            smtp_auth=SmtpAuthConfig(username=None, password="test"),  # type: ignore
        )


@pytest.mark.parametrize(
    "smtp_auth",
    [
        SmtpAuthConfig(username="bob@bobswebsite.com", password=SecretStr("passw0rd")),
        SmtpAuthConfig(username="bob@bobswebsite.com", password=SecretStr("")),
        SmtpAuthConfig(username="", password=SecretStr("passw0rd")),
        None,
    ],
    ids=["WithUsernameAndPassword", "BlankPassword", "BlankUsername", "NoAuth"],
)
async def test_smtp_authentication(smtp_auth: SmtpAuthConfig | None):
    """Verify that authentication is only used when credentials are configured."""
    config = SmtpClientConfig(smtp_host="127.0.0.1", smtp_port=587, smtp_auth=smtp_auth)

    mock_server = Mock(spec=smtplib.SMTP)
    mock_server.noop.side_effect = lambda: (250, b"")

    smtp_client = SmtpClient(config=config)

    @contextmanager
    def get_mock_server():
        yield mock_server

    smtp_client.get_connection = get_mock_server  # type: ignore [method-assign]

    message = EmailMessage()
    message["To"] = "to@example.com"
    message["Subject"] = "Test"
    message["From"] = "from@example.com"

    smtp_client.send_email_message(message)

    # Verify that 'login' is only called when credentials are set
    if smtp_auth:
        mock_server.login.assert_called()
    else:
        mock_server.login.assert_not_called()

    # Verify that 'send_message' is called regardless
    mock_server.send_message.assert_called()


async def test_failed_authentication(joint_fixture: JointFixture):
    """Test that we raise the expected error when auth fails on a secured SMTP server."""
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
        type_=joint_fixture.config.notification_type,
        topic=joint_fixture.config.notification_topic,
    )

    with pytest.raises(SmtpClient.ConnectionAttemptError):
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
    concatenated = TEST_CORRELATION_ID + json.dumps(
        notification.model_dump(), sort_keys=True
    )
    expected_record = NotificationRecord(
        hash_sum=sha256(concatenated.encode("utf-8")).hexdigest(), sent=False
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
        type_=joint_fixture.config.notification_type,
        topic=joint_fixture.config.notification_topic,
    )

    # generate the hash sum for the notification
    record = joint_fixture.notifier._create_notification_record(
        notification=notification_event
    )

    # verify the hash is generated with the keys sorted and correlation ID prepended
    concatenated = TEST_CORRELATION_ID + json.dumps(
        notification_event.model_dump(), sort_keys=True
    )
    assert record.hash_sum == sha256(concatenated.encode("utf-8")).hexdigest()

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
        type_=joint_fixture.config.notification_type,
        topic=joint_fixture.config.notification_topic,
    )

    # Consume the event, which should NOT send anything and create no ConnectionError
    # For clarification for anyone visiting this after a while, the ConnectionError
    # would be raised if it tried to connect to an actual server because the config
    # is bogus. If no ConnectionError is raised, that means the Notifier didn't try
    # to send an email.
    await joint_fixture.event_subscriber.run(forever=False)


async def test_html_escaping(joint_fixture: JointFixture):
    """Make sure dirty args are escaped properly in the HTML email and unchanged in the
    plaintext email.
    """
    # Cast notifier type
    joint_fixture.notifier = cast(Notifier, joint_fixture.notifier)

    original_body = "<script>alert('danger');</script>"
    original_name = f"<p>{sample_notification['recipient_name']}</p>"
    injected_notification = {**sample_notification}
    injected_notification["plaintext_body"] = original_body
    injected_notification["recipient_name"] = original_name

    # Precompute the escaped values and make sure they're not the same as the original
    escaped_name = html.escape(original_name)
    escaped_body = html.escape(original_body)
    assert original_name != escaped_name
    assert original_body != escaped_body

    notification = make_notification(injected_notification)

    msg = joint_fixture.notifier._construct_email(notification=notification)
    assert msg is not None

    plaintext_body = msg.get_body(preferencelist="plain")
    assert plaintext_body is not None

    plaintext_content = plaintext_body.get_content()
    expected_plaintext = (
        f"Dear {original_name},\n\n{original_body}\n"
        + "\nWarm regards,\n\nThe GHGA Team"
    )
    assert plaintext_content.strip() == expected_plaintext

    html_body = msg.get_body(preferencelist="html")
    assert html_body is not None

    html_content = html_body.get_content()
    assert html_content is not None

    expected_html = (
        '<!DOCTYPE html><html><head></head><body style="color: #00393f;'
        + f'padding: 12px;"><h2>Dear {escaped_name},</h2><p>{escaped_body}</p>'
        + "<p>Warm regards,</p><h3>The GHGA Team</h3>"
        + "</body></html>"
    )
    assert html_content.strip() == expected_html


@pytest.mark.parametrize("port", [443, 0])
async def test_timeout(port: int):
    """Test that the SMTP timeout works as expected."""
    client_config = SmtpClientConfig(
        smtp_auth=None, smtp_host="localhost", smtp_port=port, smtp_timeout=1
    )
    config = get_config(sources=[client_config])
    smtp_client = SmtpClient(config=config)
    dao_mock = AsyncMock()
    dao_mock.get_by_id.side_effect = ResourceNotFoundError(id_="test")

    notifier = Notifier(
        config=config, smtp_client=smtp_client, notification_record_dao=dao_mock
    )
    with pytest.raises(smtp_client.ConnectionAttemptError):
        await notifier.send_notification(
            notification=make_notification(sample_notification)
        )
