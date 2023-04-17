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

"""Test basic event consumption"""
import pytest
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.akafka.testutils import kafka_fixture  # noqa: F401

from ns.core.notifier import Notifier
from tests.fixtures.config import get_config
from tests.fixtures.joint import JointFixture, joint_fixture  # noqa: F401


@pytest.mark.asyncio
async def test_basic_path(joint_fixture: JointFixture):  # noqa: F811
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

    event_subscriber = await joint_fixture.container.kafka_event_subscriber()
    with pytest.raises(NotImplementedError):
        await event_subscriber.run(forever=False)


@pytest.mark.asyncio
async def test_email_construction():
    """Verify that the email is getting constructed properly from the template."""
    notification = event_schemas.Notification(
        recipient_email="test@example.com",
        email_cc=[],
        email_bcc=[],
        subject="Test123",
        recipient_name="Yolanda Martinez",
        plaintext_body="Where are you, where are you, Yolanda?",
    )

    notifier = Notifier(config=get_config())
    msg = notifier._construct_email(
        notification=notification
    )  # pylint: disable=protected-access

    assert msg is not None

    plaintext_body = msg.get_body(preferencelist=("plain"))
    assert plaintext_body is not None

    plaintext_content = plaintext_body.get_content()  # type: ignore[attr-defined]
    expected_plaintext = "Dear Yolanda Martinez,\n\nWhere are you, where are you, Yolanda?\n\nWarm regards,\n\nThe GHGA Team"
    assert plaintext_content.strip() == expected_plaintext

    html_body = msg.get_body(preferencelist=("html"))
    assert html_body is not None

    html_content = html_body.get_content()  # type: ignore[attr-defined]
    assert html_content is not None

    expected_html = '<!DOCTYPE html><html><head></head><body style="color: #00393f;padding: 12px;"><h2>Dear Yolanda Martinez,</h2><p>Where are you, where are you, Yolanda?</p><p>Warm regards,</p><h3>The GHGA Team</h3></body></html>'
    assert html_content.strip() == expected_html
