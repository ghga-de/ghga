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

"""Test basic event consumption"""

import json
from unittest.mock import Mock
from uuid import UUID

import pytest

from hexkit.correlation import correlation_id_var
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from ns.adapters.outbound.lox24_client import Lox24Client
from ns.adapters.outbound.smtp_client import SmtpClient
from ns.core.notifier import Notifier
from ns.inject import prepare_event_subscriber
from tests.fixtures.config import get_config
from tests.fixtures.joint import (
    JointFixture,
)
from tests.fixtures.utils import make_sms_notification

pytestmark = pytest.mark.asyncio()

TEST_CORRELATION_ID = UUID("6914c8cd-1f18-43da-ac6c-c43cca3f36cc")

TEST_EVENT_ID = UUID("f8b1c5d2-3e4f-4a5b-8c6d-7e8f9a0b1c2d")


SAMPLE_SMS_NOTIFICATION = {
    "phone": "+491234567890",
    "text": "Where are you, where are you, Yolanda?",
}


LOX24_STATUS_CODES = [
    {
        "status_code": 201,
        "exception": None,
    },
    {
        "status_code": 401,
        "exception": Lox24Client.AccountError,
    },
    {
        "status_code": 402,
        "exception": Lox24Client.AccountError,
    },
    {
        "status_code": 403,
        "exception": Lox24Client.AccountError,
    },
    {
        "status_code": 400,
        "exception": Lox24Client.RequestError,
    },
    {
        "status_code": 404,
        "exception": Lox24Client.RequestError,
    },
    {
        "status_code": 500,
        "exception": Lox24Client.SystemError,
    },
    {
        "status_code": 502,
        "exception": Lox24Client.SystemError,
    },
    {
        "status_code": 503,
        "exception": Lox24Client.SystemError,
    },
    {
        "status_code": 504,
        "exception": Lox24Client.SystemError,
    },
    {
        "status_code": 501,
        "exception": Lox24Client.GeneralSmsException,
    },
]


def expected_sms_payload(joint_fixture: JointFixture) -> dict[str, str]:
    """The exact payload the Lox24 gateway should receive for the sample notification."""
    return {
        **SAMPLE_SMS_NOTIFICATION,
        "sender_id": joint_fixture.config.lox24_sender_id,
    }


@pytest.fixture(autouse=True)
def correlation_id_fixture():
    """Provides a new correlation ID for each test case."""
    # we cannot use an async fixture with set_correlation_id(),
    # because it would run in a different context from the test
    token = correlation_id_var.set(TEST_CORRELATION_ID)
    yield
    correlation_id_var.reset(token)


async def test_sms_notification(joint_fixture: JointFixture):
    """Basic test"""
    assert not joint_fixture.config.kafka_enable_dlq
    joint_fixture.lox24.expected_json = expected_sms_payload(joint_fixture)
    notification_event = make_sms_notification(SAMPLE_SMS_NOTIFICATION)

    await joint_fixture.kafka.publish_event(
        payload=notification_event.model_dump(),
        type_=joint_fixture.config.sms_notification_type,
        topic=joint_fixture.config.notification_topic,
        event_id=TEST_EVENT_ID,
    )

    await joint_fixture.event_subscriber.run(forever=False)
    joint_fixture.lox24.validate_requests()
    requests_made = joint_fixture.lox24.requests
    assert len(requests_made) == 1
    request = requests_made[0]
    assert request.headers["host"] == "api.lox24.eu"
    assert request.method == "POST"
    request_data = json.loads(request.content.decode())
    assert request_data["phone"] == SAMPLE_SMS_NOTIFICATION["phone"]
    assert request_data["text"] == SAMPLE_SMS_NOTIFICATION["text"]
    assert request_data["sender_id"] == joint_fixture.config.lox24_sender_id


async def test_send_sms_not_email(
    kafka: KafkaFixture,
    mongodb: MongoDbFixture,
):
    """Test that when an SMS notification is sent, no email is sent."""
    config = get_config(sources=[kafka.config, mongodb.config])
    assert not config.kafka_enable_dlq

    sms_client = Mock(spec=Lox24Client)
    smtp_mock = Mock(spec=SmtpClient)
    notifier = Notifier(config=config, smtp_client=smtp_mock, sms_client=sms_client)
    notification_event = make_sms_notification(SAMPLE_SMS_NOTIFICATION)

    await kafka.publish_event(
        payload=notification_event.model_dump(),
        type_=config.sms_notification_type,
        topic=config.notification_topic,
        event_id=TEST_EVENT_ID,
    )

    async with (
        prepare_event_subscriber(
            config=config, notifier_override=notifier
        ) as event_subscriber,
    ):
        await event_subscriber.run(forever=False)

    assert smtp_mock.send_email_message.assert_not_called
    assert sms_client.send_sms_message.assert_called_once


@pytest.mark.parametrize("response", LOX24_STATUS_CODES)
async def test_failures(
    response: dict,
    joint_fixture: JointFixture,
):
    """Test that in case of a failure no SMS is sent"""
    assert not joint_fixture.config.kafka_enable_dlq

    joint_fixture.lox24.status_code = response["status_code"]
    joint_fixture.lox24.expected_json = expected_sms_payload(joint_fixture)
    notification_event = make_sms_notification(SAMPLE_SMS_NOTIFICATION)

    await joint_fixture.kafka.publish_event(
        payload=notification_event.model_dump(),
        type_=joint_fixture.config.sms_notification_type,
        topic=joint_fixture.config.notification_topic,
        event_id=TEST_EVENT_ID,
    )

    # Consume the event, which should throw an exception
    if response["exception"]:
        with pytest.raises(response["exception"]):
            await joint_fixture.event_subscriber.run(forever=False)
    else:
        await joint_fixture.event_subscriber.run(forever=False)
    # Assert a request has been made
    assert len(joint_fixture.lox24.requests) == 1

    joint_fixture.lox24.validate_requests()
