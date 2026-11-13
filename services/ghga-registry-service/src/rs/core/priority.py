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

"""Logic for managing the priority order of the upload boxes."""

import logging
from collections.abc import Callable, Mapping

from pydantic import UUID4

from hexkit.protocols.dao import (
    PreconditionFailedError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    race_condition_retries,
)
from hexkit.utils import now_utc_ms_prec
from rs.constants import BOX_PRIORITY_EVENT_KEY
from rs.core.models import (
    ResearchDataUploadBox,
    UploadBoxPriority,
    UploadBoxPriorityEntry,
    UploadBoxPriorityMove,
    UploadBoxPriorityResponse,
    UploadBoxPrioritySaveResult,
)
from rs.ports.inbound.priority import UploadBoxPriorityManagerPort
from rs.ports.outbound.audit import AuditRepositoryPort
from rs.ports.outbound.dao import BoxDao, UploadBoxPriorityDao

log = logging.getLogger(__name__)

__all__ = ["UploadBoxPriorityManager"]

# Changes the list of research data upload box IDs that the priority list holds
BoxIdsChange = Callable[[list[UUID4]], list[UUID4]]


def _with_missing_boxes(
    box_ids: list[UUID4], boxes: Mapping[UUID4, ResearchDataUploadBox]
) -> list[UUID4]:
    """Append the boxes in `boxes` that have no entry in `box_ids` yet, oldest
    `last_changed` first.

    RS writes a box and the list separately, so a box created since the last write to
    the list has no entry yet. Before the first list is stored, no box has one.
    """
    listed = set(box_ids)
    missing = sorted(
        (box for box_id, box in boxes.items() if box_id not in listed),
        key=lambda box: (box.last_changed, box.id),
    )
    return [*box_ids, *(box.id for box in missing)]


def _apply_moves(
    box_ids: list[UUID4], moves: list[UploadBoxPriorityMove]
) -> tuple[list[UUID4], list[UploadBoxPriorityMove]]:
    """Apply the moves to `box_ids` in order, and return the result and the skipped
    moves.

    A move of a box that is not in the list inserts it. A move is skipped if `before`
    is neither None nor in the list, or is the moved box itself.
    """
    box_ids = list(box_ids)
    skipped: list[UploadBoxPriorityMove] = []
    for move in moves:
        if move.before == move.box_id or (
            move.before is not None and move.before not in box_ids
        ):
            skipped.append(move)
            continue
        if move.box_id in box_ids:
            box_ids.remove(move.box_id)
        position = len(box_ids) if move.before is None else box_ids.index(move.before)
        box_ids.insert(position, move.box_id)
    return box_ids, skipped


class UploadBoxPriorityManager(UploadBoxPriorityManagerPort):
    """A class for managing the priority order of the upload boxes.

    RS writes a box and the list separately, so every write to the list also repairs
    it: it adds the missing boxes before the change, and drops the entries for
    unknown, archived and deleted boxes after it.
    """

    def __init__(
        self,
        *,
        priority_dao: UploadBoxPriorityDao,
        box_dao: BoxDao,
        audit_repository: AuditRepositoryPort,
    ):
        self._priority_dao = priority_dao
        self._box_dao = box_dao
        self._audit_repository = audit_repository

    async def repair(self, *, user_id: UUID4 | None = None) -> None:
        """Repair the priority list on behalf of a user, or of the system if None.

        The repair adds missing boxes to the end, oldest `last_changed` first, and
        drops the entries for boxes that are archived or no longer exist. Writes
        nothing if the list is already complete. RS runs it once at startup on behalf
        of the system, and after a data steward creates, archives or deletes a box on
        behalf of that steward.

        Raises:
            PriorityUpdateError: If other writes kept changing the list first.
        """
        await self._update_priority(user_id=user_id)

    async def get_priority(self) -> UploadBoxPriorityResponse:
        """Get the stored priority list, or an empty one with version 0 if none is
        stored yet.
        """
        return UploadBoxPriorityResponse.from_priority(
            await self._get_stored_priority()
        )

    async def move_boxes(
        self, *, version: int, moves: list[UploadBoxPriorityMove], user_id: UUID4
    ) -> UploadBoxPrioritySaveResult:
        """Apply the moves of a data steward to the stored priority list, in order.

        Adds the missing boxes before the moves, and drops the entries for unknown,
        archived and deleted boxes after the last move, so that later moves can refer
        to such a box. A move of a box that is not in the list inserts it. A move is
        skipped if `before` is neither None nor in the list, or is the moved box
        itself. A skipped move does not stop the moves after it. `version` is the
        version the moves were made on, and only sets `includes_other_changes`.

        Raises:
            PriorityUpdateError: If other writes kept changing the list first.
        """
        skipped: list[UploadBoxPriorityMove] = []

        def change(box_ids: list[UUID4]) -> list[UUID4]:
            # Runs again on a fresh read after a lost race
            nonlocal skipped
            box_ids, skipped = _apply_moves(box_ids, moves)
            return box_ids

        read_version, priority = await self._update_priority(
            user_id=user_id, change=change
        )
        return UploadBoxPrioritySaveResult(
            priority=UploadBoxPriorityResponse.from_priority(priority),
            skipped=skipped,
            includes_other_changes=read_version != version,
        )

    async def _get_stored_priority(self) -> UploadBoxPriority | None:
        """Get the stored priority list, or None if none was stored yet."""
        try:
            return await self._priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
        except ResourceNotFoundError:
            return None

    async def _update_priority(
        self, *, user_id: UUID4 | None, change: BoxIdsChange | None = None
    ) -> tuple[int, UploadBoxPriority | None]:
        """Apply `change` to the priority list and repair it, retrying on a lost race.

        Each attempt reads the list and the boxes, adds the missing boxes, applies the
        change, and drops the entries for unknown/archived/deleted boxes. The
        result is written only if the stored `version` is unchanged.
        If the result is the same as the stored list, return early.

        Returns the version the successful attempt read, or 0 if no list was stored,
        and the stored list after the update. The list is None if none is stored and
        none is needed because there is no box.

        Raises:
            PriorityUpdateError: If other writes kept changing the list first.
        """
        async for attempt in race_condition_retries(
            description="update the upload box priority list",
            error_on_failure=self.PriorityUpdateError,
            logger=log,
            # One list write takes milliseconds, and box requests wait for it
            interval=0.1,
            jitter=0.1,
        ):
            with attempt:
                stored = await self._get_stored_priority()
                read_version = stored.version if stored else 0
                boxes = {
                    box.id: box
                    async for box in self._box_dao.find_all(
                        filter_={"state": {"$ne": "archived"}}
                    )
                }
                old_box_ids = (
                    [entry.research_data_upload_box_id for entry in stored.entries]
                    if stored
                    else []
                )
                box_ids = _with_missing_boxes(old_box_ids, boxes)
                if change:
                    box_ids = change(box_ids)
                entries = [
                    UploadBoxPriorityEntry(
                        research_data_upload_box_id=box_id,
                        file_upload_box_id=boxes[box_id].file_upload_box_id,
                    )
                    for box_id in box_ids
                    if box_id in boxes
                ]
                if stored is None and not entries:
                    return read_version, None
                if stored is not None and entries == stored.entries:
                    return read_version, stored

                new_priority = UploadBoxPriority(
                    id=BOX_PRIORITY_EVENT_KEY,
                    version=read_version + 1,
                    changed_by=user_id,
                    last_changed=now_utc_ms_prec(),
                    entries=entries,
                )
                if stored:
                    await self._priority_dao.update(
                        new_priority, precondition={"version": stored.version}
                    )
                else:
                    try:
                        await self._priority_dao.insert(new_priority)
                    except ResourceAlreadyExistsError as err:
                        # Another write stored the first list in the meantime, so
                        # start again, as after any other lost race
                        raise PreconditionFailedError(
                            id_=BOX_PRIORITY_EVENT_KEY, precondition={"version": 0}
                        ) from err

                await self._audit_repository.log_box_priority_updated(
                    priority=new_priority, old_box_ids=old_box_ids, user_id=user_id
                )
                return read_version, new_priority

        # Not reached: race_condition_retries raises once the last attempt failed
        raise self.PriorityUpdateError()
