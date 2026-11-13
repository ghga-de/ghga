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

"""Port definition for the UploadBoxPriorityManager."""

from abc import ABC, abstractmethod

from pydantic import UUID4

from rs.core.models import (
    UploadBoxPriorityMove,
    UploadBoxPriorityResponse,
    UploadBoxPrioritySaveResult,
)


class UploadBoxPriorityManagerPort(ABC):
    """Port for a class that manages the priority order of the upload boxes.

    The order decides which box's files are re-encrypted first. It holds every
    research data- and file upload box ID that is not archived.
    """

    class PriorityUpdateError(RuntimeError):
        """Raised when the priority list could not be written because other writes
        kept changing it first.
        """

        def __init__(self) -> None:
            super().__init__(
                "Could not update the upload box priority list because it kept"
                + " changing."
            )

    @abstractmethod
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
        ...

    @abstractmethod
    async def get_priority(self) -> UploadBoxPriorityResponse:
        """Get the stored priority list, or an empty one with version 0 if none is
        stored yet.
        """
        ...

    @abstractmethod
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
        ...
