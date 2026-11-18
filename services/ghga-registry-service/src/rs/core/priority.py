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
    UploadBoxPriorityResponse,
)
from rs.ports.inbound.priority import UploadBoxPriorityManagerPort
from rs.ports.outbound.audit import AuditRepositoryPort
from rs.ports.outbound.dao import BoxDao, UploadBoxPriorityDao

log = logging.getLogger(__name__)

__all__ = ["UploadBoxPriorityManager"]

# Changes the research data upload box IDs that the priority list holds, given the
# stored version they were read at
BoxIdsChange = Callable[[int, list[UUID4]], list[UUID4]]


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


class UploadBoxPriorityManager(UploadBoxPriorityManagerPort):
    """A class for managing the priority order of the upload boxes.

    RS writes a box and the list separately, so every write to the list also repairs
    it: before the change, it adds the missing boxes and drops the entries for
    unknown, archived and deleted boxes.

    Every write sets `changed_by` and `last_changed`. Only a data steward's save sets
    `reordered_by` and `reordered_at`, so the list keeps naming the steward who chose
    the order after repairs, which never reorder the boxes already listed.
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
        behalf of that steward. Keeps `reordered_by` and `reordered_at`.

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

    async def set_order(
        self, *, version: int, box_ids: list[UUID4], user_id: UUID4
    ) -> UploadBoxPriorityResponse:
        """Replace the order of the priority list with the order of a data steward.

        `box_ids` must hold every box that is not archived, once, and `version` must
        be the stored version, or 0 if no list is stored yet. Returns the stored list
        after the save, which names the steward in `reordered_by`. If the order is
        unchanged, writes nothing.

        Raises:
            PriorityChangedError: If the list changed since `version`, or does not
                hold the same boxes as `box_ids`.
        """

        def change(read_version: int, repaired_box_ids: list[UUID4]) -> list[UUID4]:
            # A lost race means another write came first, so a retry raises this too
            if read_version != version or set(repaired_box_ids) != set(box_ids):
                raise self.PriorityChangedError(version=version)
            return box_ids

        priority = await self._update_priority(user_id=user_id, change=change)
        return UploadBoxPriorityResponse.from_priority(priority)

    async def _get_stored_priority(self) -> UploadBoxPriority | None:
        """Get the stored priority list, or None if none was stored yet."""
        try:
            return await self._priority_dao.get_by_id(BOX_PRIORITY_EVENT_KEY)
        except ResourceNotFoundError:
            return None

    async def _update_priority(
        self, *, user_id: UUID4 | None, change: BoxIdsChange | None = None
    ) -> UploadBoxPriority | None:
        """Repair the priority list and apply `change` to it, retrying on a lost race.

        Each attempt reads the list and the boxes, adds the missing boxes, drops the
        entries for unknown/archived/deleted boxes, and applies the change, which gets
        the version it read, or 0 if no list is stored. The change must return only
        IDs of the boxes it got. The result is written only if the stored `version` is
        unchanged. If the result is the same as the stored list, return early.
        `reordered_by` and `reordered_at` are only updated when changes are made by a
        Data Steward - system updates (repairs, box archival, etc.) are only reflected
        in `last_changed` and `changed_by`.

        Returns the stored list after the update, or None if none is stored and none
        is needed because there is no box.

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
                box_ids = [
                    box_id
                    for box_id in _with_missing_boxes(old_box_ids, boxes)
                    if box_id in boxes
                ]
                if change:
                    box_ids = change(read_version, box_ids)
                entries = [
                    UploadBoxPriorityEntry(
                        research_data_upload_box_id=box_id,
                        file_upload_box_id=boxes[box_id].file_upload_box_id,
                    )
                    for box_id in box_ids
                ]
                if stored is None and not entries:
                    return None
                if stored is not None and entries == stored.entries:
                    return stored

                now = now_utc_ms_prec()
                if change:
                    reordered_by, reordered_at = user_id, now
                elif stored:
                    reordered_by, reordered_at = (
                        stored.reordered_by,
                        stored.reordered_at,
                    )
                else:
                    reordered_by, reordered_at = None, None
                new_priority = UploadBoxPriority(
                    id=BOX_PRIORITY_EVENT_KEY,
                    version=read_version + 1,
                    changed_by=user_id,
                    last_changed=now,
                    reordered_by=reordered_by,
                    reordered_at=reordered_at,
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
                return new_priority

        # Not reached: race_condition_retries raises once the last attempt failed
        raise self.PriorityUpdateError()
