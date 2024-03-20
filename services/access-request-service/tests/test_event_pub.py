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
from ghga_event_schemas.pydantic_ import AccessRequestDetails
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventpub import EventPublisherProtocol

from ars.adapters.outbound.event_pub import (
    EventPubTranslator,
    EventPubTranslatorConfig,
)
from ars.core.models import AccessRequest, AccessRequestStatus

pytestmark = pytest.mark.asyncio(scope="session")

dummy_config = EventPubTranslatorConfig(
    access_request_allowed_event_type="access_request_allowed",
    access_request_created_event_type="access_request_created",
    access_request_denied_event_type="access_request_denied",
    access_request_events_topic="access_requests",
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


event_publisher = EventPubTranslator(
    config=dummy_config, event_publisher=event_recorder
)


@pytest.mark.parametrize("status", ["created", "allowed", "denied"])
async def test_access_request_events(status: str):
    """Test that an event is published properly."""
    request = AccessRequest(
        id="unique_access_request_id",
        user_id="user123",
        dataset_id="dataset456",
        email="requester@example.com",
        request_text="Requesting access for research purposes",
        access_starts=now_as_utc(),
        access_ends=now_as_utc(),
        full_user_name="Dr. Jane Doe",
        request_created=now_as_utc(),
        status=AccessRequestStatus.PENDING,
        status_changed=None,
        changed_by=None,
    )

    publish_method = getattr(event_publisher, f"publish_request_{status}")
    await publish_method(request=request)

    expected_topic = dummy_config.access_request_events_topic
    expected_type = getattr(dummy_config, f"access_request_{status}_event_type")
    expected_payload = AccessRequestDetails(
        user_id=request.user_id, dataset_id=request.dataset_id
    ).model_dump()

    assert event_recorder.recorded_event == {
        "type": expected_type,
        "key": request.user_id,
        "topic": expected_topic,
        **expected_payload,
    }
