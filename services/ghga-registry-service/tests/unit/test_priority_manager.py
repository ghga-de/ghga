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

"""Unit tests for the UploadBoxPriorityManager"""

from dataclasses import dataclass
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from hexkit.protocols.dao import PreconditionFailedError, ResourceNotFoundError
from hexkit.providers.testing.dao import BaseInMemDao, new_mock_dao_class
from hexkit.utils import now_utc_ms_prec
from rs.constants import BOX_PRIORITY_EVENT_KEY
from rs.core import models
from rs.core.priority import UploadBoxPriorityManager
from rs.ports.inbound.priority import UploadBoxPriorityManagerPort
from tests.fixtures.utils import TEST_DS_ID, TEST_MAX_SIZE

pytestmark = pytest.mark.asyncio

InMemBoxDao = new_mock_dao_class(dto_model=models.ResearchDataUploadBox, id_field="id")
InMemPriorityDao = new_mock_dao_class(dto_model=models.UploadBoxPriority, id_field="id")


@dataclass
class PriorityRig:
    """The UploadBoxPriorityManager plus its in-memory dependencies."""

    box_dao: BaseInMemDao[models.ResearchDataUploadBox]
    priority_dao: BaseInMemDao[models.UploadBoxPriority]
    audit_repository: AsyncMock
    priority_manager: UploadBoxPriorityManager


@pytest.fixture(name="rig")
def rig_fixture() -> PriorityRig:
    """Return an UploadBoxPriorityManager with in-memory dependencies."""
    box_dao = InMemBoxDao()
    priority_dao = InMemPriorityDao()
    audit_repository = AsyncMock()
    priority_manager = UploadBoxPriorityManager(
        priority_dao=priority_dao,
        box_dao=box_dao,
        audit_repository=audit_repository,
    )
    return PriorityRig(
        box_dao=box_dao,
        priority_dao=priority_dao,
        audit_repository=audit_repository,
        priority_manager=priority_manager,
    )


def _make_box(
    *, days_ago: int, state: models.UploadBoxState = "open"
) -> models.ResearchDataUploadBox:
    """Make a box that was last changed the given number of days ago."""
    return models.ResearchDataUploadBox(
        version=0,
        state=state,
        title=f"Box {uuid4()}",
        description="A box for the priority tests",
        last_changed=now_utc_ms_prec() - timedelta(days=days_ago),
        changed_by=TEST_DS_ID,
        file_upload_box_id=uuid4(),
        file_upload_box_version=0,
        file_upload_box_state=state,
        storage_alias="HD01",
        max_size=TEST_MAX_SIZE,
    )


async def _store_boxes(rig: PriorityRig, *boxes: models.ResearchDataUploadBox):
    """Store the given boxes."""
    for box in boxes:
        await rig.box_dao.insert(box)


def _entries(
    *boxes: models.ResearchDataUploadBox,
) -> list[models.UploadBoxPriorityEntry]:
    """Make the priority entries for the given boxes, in the given order."""
    return [
        models.UploadBoxPriorityEntry(
            research_data_upload_box_id=box.id,
            file_upload_box_id=box.file_upload_box_id,
        )
        for box in boxes
    ]


def _make_priority(
    *, version: int, entries: list[models.UploadBoxPriorityEntry]
) -> models.UploadBoxPriority:
    """Make a priority list that a data steward changed a day ago."""
    return models.UploadBoxPriority(
        id=BOX_PRIORITY_EVENT_KEY,
        version=version,
        changed_by=TEST_DS_ID,
        last_changed=now_utc_ms_prec() - timedelta(days=1),
        entries=entries,
    )


async def test_repair_without_boxes(rig: PriorityRig):
    """Test that the repair stores no list if there is no box."""
    await rig.priority_manager.repair()

    with pytest.raises(ResourceNotFoundError):
        await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
    rig.audit_repository.log_box_priority_updated.assert_not_awaited()


async def test_repair_fills_new_list(rig: PriorityRig):
    """Test that the first repair lists every box that is not archived, oldest
    `last_changed` first, on behalf of the system.
    """
    newer = _make_box(days_ago=1)
    older = _make_box(days_ago=2, state="locked")
    archived = _make_box(days_ago=3, state="archived")
    await _store_boxes(rig, newer, older, archived)
    started = now_utc_ms_prec()

    await rig.priority_manager.repair()

    priority = await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
    assert priority.version == 1
    assert priority.changed_by is None
    assert priority.last_changed >= started
    assert priority.entries == _entries(older, newer)
    rig.audit_repository.log_box_priority_updated.assert_awaited_once_with(
        priority=priority, old_box_ids=[], user_id=None
    )


async def test_repair_heals_list(rig: PriorityRig):
    """Test that the repair drops the entries for archived or deleted boxes and
    appends the missing boxes, keeping the order of the listed ones.
    """
    first = _make_box(days_ago=4)
    second = _make_box(days_ago=3)
    missing = _make_box(days_ago=5)
    archived = _make_box(days_ago=2, state="archived")
    deleted = _make_box(days_ago=1)  # never stored
    await _store_boxes(rig, first, second, missing, archived)
    await rig.priority_dao.insert(
        _make_priority(version=3, entries=_entries(second, deleted, archived, first))
    )

    await rig.priority_manager.repair()

    priority = await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
    assert priority.version == 4
    assert priority.changed_by is None
    assert priority.entries == _entries(second, first, missing)
    rig.audit_repository.log_box_priority_updated.assert_awaited_once_with(
        priority=priority,
        old_box_ids=[second.id, deleted.id, archived.id, first.id],
        user_id=None,
    )


async def test_repair_of_complete_list(rig: PriorityRig):
    """Test that the repair writes nothing if the list is already complete."""
    box = _make_box(days_ago=1)
    await _store_boxes(rig, box)
    stored = _make_priority(version=3, entries=_entries(box))
    await rig.priority_dao.insert(stored)

    await rig.priority_manager.repair()

    assert await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY) == stored
    rig.audit_repository.log_box_priority_updated.assert_not_awaited()


async def test_repair_on_behalf_of_user(rig: PriorityRig):
    """Test that a repair after a box change adds a new box to the end of the list
    and drops a deleted one, each on behalf of the given user.
    """
    listed = _make_box(days_ago=2)
    new = _make_box(days_ago=0)
    await _store_boxes(rig, listed, new)
    await rig.priority_dao.insert(_make_priority(version=1, entries=_entries(listed)))
    audit = rig.audit_repository.log_box_priority_updated

    await rig.priority_manager.repair(user_id=TEST_DS_ID)

    priority = await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
    assert priority.version == 2
    assert priority.changed_by == TEST_DS_ID
    assert priority.entries == _entries(listed, new)
    audit.assert_awaited_once_with(
        priority=priority, old_box_ids=[listed.id], user_id=TEST_DS_ID
    )

    await rig.box_dao.delete(listed.id)
    await rig.priority_manager.repair(user_id=TEST_DS_ID)

    priority = await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
    assert priority.version == 3
    assert priority.changed_by == TEST_DS_ID
    assert priority.entries == _entries(new)
    assert audit.await_count == 2
    audit.assert_awaited_with(
        priority=priority, old_box_ids=[listed.id, new.id], user_id=TEST_DS_ID
    )


async def test_change_by_user(rig: PriorityRig):
    """Test that a change sees the missing boxes, that the entries for unknown boxes
    are dropped after it, and that the user who made it is recorded.
    """
    listed = _make_box(days_ago=2)
    missing = _make_box(days_ago=1)
    await _store_boxes(rig, listed, missing)
    await rig.priority_dao.insert(_make_priority(version=1, entries=_entries(listed)))
    unknown_box_id = uuid4()

    def change(box_ids: list[UUID]) -> list[UUID]:
        assert box_ids == [listed.id, missing.id]
        return [unknown_box_id, missing.id, listed.id]

    priority = await rig.priority_manager._update_priority(
        user_id=TEST_DS_ID, change=change
    )

    assert priority == await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
    assert priority.version == 2
    assert priority.changed_by == TEST_DS_ID
    assert priority.entries == _entries(missing, listed)


async def test_retry_after_lost_race(rig: PriorityRig, monkeypatch: pytest.MonkeyPatch):
    """Test that a write that collides with another write is retried with a fresh
    read, so that the changes of both writes are kept.
    """
    first = _make_box(days_ago=3)
    second = _make_box(days_ago=2)
    missing = _make_box(days_ago=1)
    await _store_boxes(rig, first, second, missing)
    stored = _make_priority(version=1, entries=_entries(first, second))
    await rig.priority_dao.insert(stored)
    original_update = rig.priority_dao.update

    async def update_after_other_write(dto, *, precondition=None):
        # Another write moves the second box to the top before this write is stored
        monkeypatch.setattr(rig.priority_dao, "update", original_update)
        await original_update(
            stored.model_copy(update={"version": 2, "entries": _entries(second, first)})
        )
        await original_update(dto, precondition=precondition)

    monkeypatch.setattr(rig.priority_dao, "update", update_after_other_write)

    await rig.priority_manager.repair()

    priority = await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
    assert priority.version == 3
    assert priority.entries == _entries(second, first, missing)
    rig.audit_repository.log_box_priority_updated.assert_awaited_once_with(
        priority=priority, old_box_ids=[second.id, first.id], user_id=None
    )


async def test_retry_after_lost_race_for_first_list(
    rig: PriorityRig, monkeypatch: pytest.MonkeyPatch
):
    """Test that a first write is retried if another write stored the first list in
    the meantime.
    """
    box = _make_box(days_ago=2)
    other_box = _make_box(days_ago=1)
    await _store_boxes(rig, box, other_box)
    original_insert = rig.priority_dao.insert

    async def insert_after_other_write(dto):
        await original_insert(_make_priority(version=1, entries=_entries(other_box)))
        await original_insert(dto)

    monkeypatch.setattr(rig.priority_dao, "insert", insert_after_other_write)

    await rig.priority_manager.repair()

    priority = await rig.priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
    assert priority.version == 2
    assert priority.entries == _entries(other_box, box)


async def test_give_up_after_three_lost_races(
    rig: PriorityRig, monkeypatch: pytest.MonkeyPatch
):
    """Test that the write gives up after losing its race three times in a row."""
    box = _make_box(days_ago=1)
    await _store_boxes(rig, box)
    await rig.priority_dao.insert(_make_priority(version=1, entries=[]))
    lose_race = AsyncMock(
        side_effect=PreconditionFailedError(
            id_=BOX_PRIORITY_EVENT_KEY, precondition={"version": 1}
        )
    )
    monkeypatch.setattr(rig.priority_dao, "update", lose_race)

    with pytest.raises(UploadBoxPriorityManagerPort.PriorityUpdateError):
        await rig.priority_manager.repair()

    assert lose_race.await_count == 3
    rig.audit_repository.log_box_priority_updated.assert_not_awaited()
