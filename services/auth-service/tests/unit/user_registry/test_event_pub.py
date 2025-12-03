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
#

"""Test the translator for publishing notification events in isolation."""

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

import pytest
from hexkit.custom_types import Ascii, JsonObject
from hexkit.protocols.eventpub import EventPublisherProtocol
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from auth_service.user_registry.models.ivas import Iva, IvaState, IvaType
from auth_service.user_registry.translators.event_pub import (
    EventPubTranslator,
    EventPubTranslatorConfig,
)

default_config = EventPubTranslatorConfig(
    auth_topic="auth",
    second_factor_recreated_type="second_factor_recreated",
    iva_state_changed_topic="ivas",
    iva_state_changed_type="iva_state_changed",
    iva_send_code_type="iva_send_code",
)

custom_config = default_config.model_copy(
    update={
        "auth_topic": "custom_auth",
        "second_factor_recreated_type": "custom_second_factor_recreated",
        "iva_state_changed_topic": "custom_ivas",
        "iva_state_changed_type": "custom_iva_state_changed",
        "iva_send_code_type": "custom_iva_send_code",
    }
)

pytestmark = [
    pytest.mark.parametrize(
        "config",
        (default_config, custom_config),
        ids=("default_config", "custom_config"),
    ),
    pytest.mark.asyncio(loop_scope="package"),
]


class MockEventPublisher(EventPublisherProtocol):
    """A event publisher mock for testing."""

    def __init__(
        self, expected_topic: str = "dummy_topic", expected_type: str = "dummy_event"
    ):
        self.expected_topic = expected_topic
        self.expected_type = expected_type
        self.published_key: str | None = None
        self.published_payload: dict | None = None

    async def _publish_validated(
        self,
        *,
        payload: JsonObject,
        type_: Ascii,
        key: Ascii,
        topic: Ascii,
        event_id: UUID4,
        headers: Mapping[str, Any],
    ) -> None:
        """Record a published event and test expectations."""
        assert topic == self.expected_topic
        assert type_ == self.expected_type
        assert isinstance(key, str)
        self.published_key = key
        assert isinstance(payload, dict)
        self.published_payload = payload


class AuthEventPublisher(MockEventPublisher):
    """A event publisher for testing auth related notifications."""

    def __init__(self, config: EventPubTranslatorConfig):
        super().__init__(config.auth_topic, config.second_factor_recreated_type)


async def test_publish_2fa_recreated(config: EventPubTranslatorConfig):
    """Test publishing a 2FA setup recreation event for a user."""
    publisher = AuthEventPublisher(config)
    translator = EventPubTranslator(config=config, event_publisher=publisher)
    user_id = uuid4()
    await translator.publish_2fa_recreated(user_id=user_id)
    assert publisher.published_key == str(user_id)
    assert publisher.published_payload == {
        "user_id": user_id,
    }


class IvaEventPublisher(MockEventPublisher):
    """A event publisher for testing IVA related notifications."""

    def __init__(self, config: EventPubTranslatorConfig):
        super().__init__(config.iva_state_changed_topic, config.iva_state_changed_type)


async def test_publish_iva_state_changed(config: EventPubTranslatorConfig):
    """Test publishing an IVA state change."""
    publisher = IvaEventPublisher(config)
    translator = EventPubTranslator(config=config, event_publisher=publisher)
    now = now_utc_ms_prec()
    iva_id = uuid4()
    iva = Iva(
        id=iva_id,
        user_id=uuid4(),
        value="123/456",
        type=IvaType.PHONE,
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    await translator.publish_iva_state_changed(iva=iva)
    assert publisher.published_key == f"iva-{iva_id}"
    assert publisher.published_payload == {
        "state": iva.state,
        "type": iva.type,
        "user_id": iva.user_id,
        "value": iva.value,
    }


async def test_publish_ivas_reset(config: EventPubTranslatorConfig):
    """Test publishing an IVA reset event for a user."""
    publisher = IvaEventPublisher(config)
    translator = EventPubTranslator(config=config, event_publisher=publisher)
    user_id = uuid4()
    await translator.publish_ivas_reset(user_id=user_id)
    assert publisher.published_key == f"all-{user_id}"
    assert publisher.published_payload == {
        "state": IvaState.UNVERIFIED,
        "type": None,
        "user_id": user_id,
        "value": None,
    }
