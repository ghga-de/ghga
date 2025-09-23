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

"""Unit tests for the auditing class"""

from contextlib import suppress
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from ghga_event_schemas.pydantic_ import (
    ResearchDataUploadBox,
    ResearchDataUploadBoxState,
)
from hexkit.correlation import get_correlation_id
from hexkit.providers.testing.eventpub import (
    Event,
    InMemEventPublisher,
    InMemEventStore,
    TopicExhaustedError,
)
from hexkit.utils import now_utc_ms_prec

from tests.fixtures import ConfigFixture
from uos.adapters.outbound.audit import AuditRepository
from uos.adapters.outbound.event_pub import EventPubTranslator

pytestmark = pytest.mark.asyncio()


AuditFixture = tuple[AuditRepository, InMemEventStore]


async def test_create_audit_record(config: ConfigFixture):
    """Test the create_audit_record method"""
    _config = config.config
    event_store = InMemEventStore()
    event_pub_translator = EventPubTranslator(
        config=_config, provider=InMemEventPublisher(event_store=event_store)
    )
    auditor = AuditRepository(service="uos", event_publisher=event_pub_translator)
    await auditor.create_audit_record(
        label="My label",
        description="Testing out my class",
        user_id=(user_id := uuid4()),
        action="C",
        entity="Test",
        entity_id=(entity_id := str(uuid4())),
    )

    # Get the event from the in memory event store
    events = []
    with suppress(TopicExhaustedError):
        while True:
            events.append(event_store.get("audit-records"))  # topic from test_config

    # Inspect the event
    assert len(events) == 1
    event: Event = events[0]
    assert event.key.startswith("uos-")
    assert event.type_ == "audit_record_logged"
    payload = dict(event.payload)
    del payload["id"]
    created = str(payload.pop("created"))  # cast to string to satisfy type checker
    assert datetime.fromisoformat(created) - now_utc_ms_prec() < timedelta(seconds=5)
    assert payload == {
        "service": "uos",
        "label": "My label",
        "description": "Testing out my class",
        "user_id": str(user_id),
        "correlation_id": str(get_correlation_id()),
        "action": "C",
        "entity": "Test",
        "entity_id": str(entity_id),
    }


async def test_log_box_created():
    """Test the log_box_created function by inspecting how it calls create_audit_record"""
    auditor = AuditRepository(service="uos", event_publisher=AsyncMock())

    # Create a test ResearchDataUploadBox
    box = ResearchDataUploadBox(
        state=ResearchDataUploadBoxState.OPEN,
        title="Test Box Title",
        description="Test box description",
        last_changed=now_utc_ms_prec(),
        changed_by=(user_id := uuid4()),
        file_upload_box_id=uuid4(),
        storage_alias="HD01",
    )

    # Call log_box_created
    auditor.create_audit_record = AsyncMock()  # type: ignore[method-assign]
    await auditor.log_box_created(box=box, user_id=user_id)
    auditor.create_audit_record.assert_called_once_with(
        label="ResearchDataUploadBox created",
        description=f"A new ResearchDataUploadBox was created with '{box.title}' (ID: {box.id}).",
        action="C",
        user_id=user_id,
        entity="ResearchDataUploadBox",
        entity_id=str(box.id),
    )


async def test_log_box_updated():
    """Test the log_box_updated function by inspecting how it calls create_audit_record"""
    auditor = AuditRepository(service="uos", event_publisher=AsyncMock())

    # Create a test ResearchDataUploadBox
    box = ResearchDataUploadBox(
        state=ResearchDataUploadBoxState.OPEN,
        title="Test Box Title",
        description="Test box description",
        last_changed=now_utc_ms_prec(),
        changed_by=(user_id := uuid4()),
        file_upload_box_id=uuid4(),
        storage_alias="HD01",
    )

    # Call log_box_updated
    auditor.create_audit_record = AsyncMock()  # type: ignore[method-assign]
    await auditor.log_box_updated(box=box, user_id=user_id)
    auditor.create_audit_record.assert_called_once_with(
        label="ResearchDataUploadBox updated",
        description=f"ResearchDataUploadBox '{box.title}' (ID: {box.id}) was updated. New state: {box.state}.",
        user_id=user_id,
        action="U",
        entity="ResearchDataUploadBox",
        entity_id=str(box.id),
    )
