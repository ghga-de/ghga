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

"""Interface for broadcasting events to other services."""

from abc import ABC, abstractmethod

from ifrs.core import models


class EventPublisherPort(ABC):
    """A port through which service-internal events are communicated with the outside."""

    @abstractmethod
    async def file_internally_registered(
        self, *, file: models.FileMetadata, bucket_id: str
    ) -> None:
        """Communicates the event that a new file has been internally registered."""
        ...

    @abstractmethod
    async def file_staged_for_download(  # noqa: PLR0913
        self,
        *,
        file_id: str,
        decrypted_sha256: str,
        target_object_id: str,
        target_bucket_id: str,
        storage_alias: str,
    ) -> None:
        """Communicates the event that a file has been staged for download"""
        ...

    @abstractmethod
    async def file_deleted(self, *, file_id: str) -> None:
        """Communicates the event that a file has been successfully deleted."""
        ...
