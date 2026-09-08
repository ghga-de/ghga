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

"""Unit tests for the auditing class"""

from contextlib import suppress
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from hexkit.correlation import get_correlation_id
from hexkit.providers.testing.eventpub import (
    Event,
    InMemEventPublisher,
    InMemEventStore,
    TopicExhaustedError,
)
from hexkit.utils import now_utc_ms_prec
from rs.adapters.outbound.audit import AuditRepository
from rs.adapters.outbound.event_pub import EventPubTranslator
from rs.config import Config
from rs.core.models import ResearchDataUploadBox
from tests.fixtures.utils import TEST_MAX_SIZE

pytestmark = pytest.mark.asyncio


AuditFixture = tuple[AuditRepository, InMemEventStore]
AUDIT_TOPIC = "audit-records"  # topic from test_config


@pytest.fixture(name="audit_fixture")
def audit_fixture(config: Config) -> AuditFixture:
    """An AuditRepository publishing to an in-memory event store, plus that store."""
    event_store = InMemEventStore()
    event_pub_translator = EventPubTranslator(
        config=config, provider=InMemEventPublisher(event_store=event_store)
    )
    auditor = AuditRepository(service="rs", event_publisher=event_pub_translator)
    return auditor, event_store


def get_audit_events(event_store: InMemEventStore) -> list[Event]:
    """Drain the audit record topic of the in-memory event store."""
    events: list[Event] = []
    with suppress(TopicExhaustedError):
        while True:
            events.append(event_store.get(AUDIT_TOPIC))
    return events


def get_audit_payload(event: Event) -> dict:
    """Return the audit record payload minus the fields that can't be predicted.

    The record's `created` timestamp is checked here since it is dropped, while the
    randomly generated `id` is simply discarded.
    """
    payload = dict(event.payload)
    del payload["id"]
    created = str(payload.pop("created"))  # cast to string to satisfy type checker
    assert datetime.fromisoformat(created) - now_utc_ms_prec() < timedelta(seconds=5)
    return payload


async def test_create_audit_record(config: Config):
    """Test the create_audit_record method"""
    _config = config
    event_store = InMemEventStore()
    event_pub_translator = EventPubTranslator(
        config=_config, provider=InMemEventPublisher(event_store=event_store)
    )
    auditor = AuditRepository(service="rs", event_publisher=event_pub_translator)
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
    assert event.key.startswith("rs-")
    assert event.type_ == "audit_record_created"
    payload = dict(event.payload)
    del payload["id"]
    created = str(payload.pop("created"))  # cast to string to satisfy type checker
    assert datetime.fromisoformat(created) - now_utc_ms_prec() < timedelta(seconds=5)
    assert payload == {
        "service": "rs",
        "label": "My label",
        "description": "Testing out my class",
        "user_id": str(user_id),
        "correlation_id": str(get_correlation_id()),
        "action": "C",
        "entity": "Test",
        "entity_id": str(entity_id),
    }


async def test_log_box_created():
    """Test the log_box_created function by inspecting how it calls
    create_audit_record.
    """
    auditor = AuditRepository(service="rs", event_publisher=AsyncMock())

    # Create a test ResearchDataUploadBox
    box = ResearchDataUploadBox(
        version=0,
        state="open",
        title="Test Box Title",
        description="Test box description",
        last_changed=now_utc_ms_prec(),
        changed_by=(user_id := uuid4()),
        file_upload_box_id=uuid4(),
        file_upload_box_version=0,
        file_upload_box_state="open",
        storage_alias="HD01",
        max_size=TEST_MAX_SIZE,
    )

    # Call log_box_created
    auditor.create_audit_record = AsyncMock()
    await auditor.log_box_created(box=box, user_id=user_id)
    auditor.create_audit_record.assert_called_once_with(
        label="ResearchDataUploadBox created",
        description=(
            f"A new ResearchDataUploadBox was created with '{box.title}'"
            f" (ID: {box.id})."
        ),
        action="C",
        user_id=user_id,
        entity="ResearchDataUploadBox",
        entity_id=str(box.id),
    )


async def test_log_box_updated():
    """Test the log_box_updated function by inspecting how it calls
    create_audit_record.
    """
    auditor = AuditRepository(service="rs", event_publisher=AsyncMock())

    # Create a test ResearchDataUploadBox
    box = ResearchDataUploadBox(
        version=0,
        state="open",
        title="Test Box Title",
        description="Test box description",
        last_changed=now_utc_ms_prec(),
        changed_by=(user_id := uuid4()),
        file_upload_box_id=uuid4(),
        file_upload_box_version=0,
        file_upload_box_state="open",
        size=10000,
        storage_alias="HD01",
        max_size=TEST_MAX_SIZE,
    )

    # Call log_box_updated
    auditor.create_audit_record = AsyncMock()
    await auditor.log_box_updated(box=box, user_id=user_id)
    auditor.create_audit_record.assert_called_once_with(
        label="ResearchDataUploadBox updated",
        description=(
            f"ResearchDataUploadBox '{box.title}' (ID: {box.id}) was updated."
            f" New state: {box.state}."
        ),
        user_id=user_id,
        action="U",
        entity="ResearchDataUploadBox",
        entity_id=str(box.id),
    )


async def test_log_box_deleted():
    """Test log_box_deleted()"""
    auditor = AuditRepository(service="rs", event_publisher=AsyncMock())
    box = ResearchDataUploadBox(
        version=0,
        state="locked",
        title="Test Box Title",
        description="Test box description",
        last_changed=now_utc_ms_prec(),
        changed_by=uuid4(),
        file_upload_box_id=uuid4(),
        file_upload_box_version=0,
        file_upload_box_state="locked",
        file_count=3,
        size=10000,
        storage_alias="HD01",
        max_size=TEST_MAX_SIZE,
    )

    user_id = uuid4()
    auditor.create_audit_record = AsyncMock()
    await auditor.log_box_deleted(box=box, user_id=user_id)
    auditor.create_audit_record.assert_called_once_with(
        label="ResearchDataUploadBox deleted",
        description=(
            f"ResearchDataUploadBox '{box.title}' (ID: {box.id}) was deleted along"
            f" with FileUploadBox {box.file_upload_box_id} containing"
            f" {box.file_count} file(s) totaling {box.size} byte(s)."
        ),
        user_id=user_id,
        action="D",
        entity="ResearchDataUploadBox",
        entity_id=str(box.id),
    )


async def test_log_file_requeued(audit_fixture: AuditFixture):
    """Test `log_file_requeued()`"""
    auditor, event_store = audit_fixture
    file_id = uuid4()
    user_id = uuid4()

    await auditor.log_file_requeued(file_id=file_id, user_id=user_id)

    # Inspect the event that was actually published
    events = get_audit_events(event_store)
    assert len(events) == 1
    event = events[0]
    assert event.key.startswith("rs-")
    assert event.type_ == "audit_record_created"
    assert get_audit_payload(event) == {
        "service": "rs",
        "label": "FileUpload requeued",
        "description": f"FileUpload {file_id} was requeued for interrogation.",
        "user_id": str(user_id),
        "correlation_id": str(get_correlation_id()),
        "action": "U",
        "entity": "FileUpload",
        "entity_id": str(file_id),
    }


async def test_log_whole_box_requeue(audit_fixture: AuditFixture):
    """Test `log_whole_box_requeued()`"""
    auditor, event_store = audit_fixture
    box_id = uuid4()
    user_id = uuid4()
    file_ids = [uuid4() for _ in range(3)]

    await auditor.log_whole_box_requeued(
        box_id=box_id, user_id=user_id, file_ids=file_ids
    )

    # Inspect the event that was actually published
    events = get_audit_events(event_store)
    assert len(events) == 1
    event = events[0]
    assert event.key.startswith("rs-")
    assert event.type_ == "audit_record_created"

    # The action is None because the box itself isn't changed, only the files in it
    assert get_audit_payload(event) == {
        "service": "rs",
        "label": "All FileUploads in ResearchDataUploadBox requeued",
        "description": (
            f"All failed FileUploads in box {box_id} were requeued for interrogation."
            + f" Requeued File IDs are: {', '.join(str(f) for f in file_ids)}."
        ),
        "user_id": str(user_id),
        "correlation_id": str(get_correlation_id()),
        "action": None,
        "entity": "ResearchDataUploadBox",
        "entity_id": str(box_id),
    }
