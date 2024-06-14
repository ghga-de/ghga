# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Describes generic functionality of a class that handles outbox event idempotence."""

from abc import ABC, abstractmethod

from ghga_event_schemas import pydantic_ as event_schemas


class IdempotenceHandlerPort(ABC):
    """Class to serve outbox event data to the core in an idempotent manner."""

    @abstractmethod
    async def upsert_nonstaged_file_requested(
        self, *, resource_id: str, update: event_schemas.NonStagedFileRequested
    ) -> None:
        """Upsert a NonStagedFileRequested event. Call `stage_registered_file` if the
        idempotence check is passed.

        Args:
            resource_id:
                The resource ID.
            update:
                The NonStagedFileRequested event to upsert.
        """
        ...

    @abstractmethod
    async def upsert_file_deletion_requested(
        self, *, resource_id: str, update: event_schemas.FileDeletionRequested
    ) -> None:
        """Upsert a FileDeletionRequested event. Call `delete_file` if the idempotence
        check is passed.

        Args:
            resource_id:
                The resource ID.
            update:
                The FileDeletionRequested event to upsert.
        """
        ...

    @abstractmethod
    async def upsert_file_upload_validation_success(
        self, *, resource_id: str, update: event_schemas.FileUploadValidationSuccess
    ) -> None:
        """Upsert a FileUploadValidationSuccess event. Call `register_file` if the
        idempotence check is passed.

        Args:
            resource_id:
                The resource ID.
            update:
                The FileUploadValidationSuccess event to upsert.
        """
        ...
