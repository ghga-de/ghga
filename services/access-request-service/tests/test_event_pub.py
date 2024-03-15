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

"""Test the translators that target the event publishing protocol."""

from typing import Any

import pytest
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventpub import EventPublisherProtocol

from ars.adapters.outbound.event_pub import (
    NotificationEmitter,
    NotificationEmitterConfig,
)

pytestmark = pytest.mark.asyncio(scope="session")

dummy_config = NotificationEmitterConfig(
    notification_event_topic="dummy_topic", notification_event_type="dummy_type"
)


class EventRecorder(EventPublisherProtocol):
    """An event publisher that records the last published event."""

    recorded_event: dict[str, Any]

    def reset(self) -> None:
        """Reset the dummy event publisher."""
        self.recorded_event = {}

    async def _publish_validated(
        self, *, payload: JsonObject, type_: Ascii, key: Ascii, topic: Ascii
    ) -> None:
        """Publish an event."""
        assert isinstance(payload, dict)
        self.recorded_event = {"type": type_, "key": key, "topic": topic, **payload}


event_recorder = EventRecorder()


notification_emitter = NotificationEmitter(
    config=dummy_config, event_publisher=event_recorder
)


async def test_sending_a_notification():
    """Test that a notification is translated properly."""
    await notification_emitter.notify(
        email="someone@somewhere.org",
        full_name="Some User Name",
        subject="Some subject",
        text="Some text",
    )
    assert event_recorder.recorded_event == {
        "recipient_email": "someone@somewhere.org",
        "recipient_name": "Some User Name",
        "email_cc": [],
        "email_bcc": [],
        "subject": "Some subject",
        "plaintext_body": "Some text",
        "topic": "dummy_topic",
        "type": "dummy_type",
        "key": "someone@somewhere.org",
    }
