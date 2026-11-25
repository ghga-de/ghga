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

"""Port for getting the files that wait for interrogation, in priority order."""

from abc import ABC, abstractmethod

from fis.core.models import BaseFileInformation, FileUnderInterrogation
from ghga_service_commons.utils.utc_dates import UTCDatetime


class InterrogationQueuePort(ABC):
    """Gets the waiting files directly from the datastore.

    Implementations rank and limit the files server-side, so only the returned files
    are loaded.
    """

    @abstractmethod
    async def get_waiting_files(
        self, *, storage_alias: str, limit: int
    ) -> list[BaseFileInformation]:
        """Return up to `limit` files of the storage alias that wait for interrogation.

        Files of boxes in the upload box priority list come first, in list order.
        Files of the same box, and files without a listed box, come in `id` order.
        """

    @abstractmethod
    async def get_claimable_files(
        self, *, storage_alias: str, claim_time: UTCDatetime, limit: int
    ) -> list[FileUnderInterrogation]:
        """Return up to `limit` waiting and not leased files for the specified storage
        alias. All of them come from the highest-priority box that has a claimable
        file.

        Boxes go by the upload box priority list. Within the box, files not yet claimed
        come first. Then come files whose lease ran out, earliest first. Ties go by
        `state_updated`.

        If for any reason a file can't be ranked (problem with the prio list, or
        box ID is missing, etc.), it gets lumped into a placeholder box with lowest
        priority.
        """
