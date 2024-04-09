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

"""Main business-logic of this service"""

from pcs.ports.inbound.file_deletion import FileDeletionPort
from pcs.ports.outbound.event_pub import EventPublisherPort


class FileDeletion(FileDeletionPort):
    """A service that commissions file deletions."""

    def __init__(
        self,
        *,
        event_publisher: EventPublisherPort,
    ):
        """Initialize with outbound adapters."""
        self._event_publisher = event_publisher

    async def delete_file(self, *, file_id: str) -> None:
        """Sends out an event to delete all occurrences of a certain file.

        Args:
            file_id: id for the file to delete.
        """
        await self._event_publisher.delete_file(file_id=file_id)
