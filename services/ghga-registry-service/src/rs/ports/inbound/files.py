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

"""Defines an inbound port for filename and file ID operations."""

from abc import ABC, abstractmethod

from pydantic import UUID4

from rs.core.models import FileAccession


class FileControllerPort(ABC):
    """Inbound port for filename and file ID operations."""

    class ConflictingAccessionError(RuntimeError):
        """Raised when a request would overwrite one or more existing immutable
        accession mappings.
        """

        def __init__(self, *, conflicting_accessions: list[str]) -> None:
            self.conflicting_accessions = conflicting_accessions
            accessions = ", ".join(conflicting_accessions)
            super().__init__(f"Conflicting accession mappings: {accessions}")

    @abstractmethod
    async def post_file_ids(
        self, *, study_id: str, file_id_map: dict[FileAccession, UUID4]
    ) -> None:
        """Store file accession to internal file ID mappings.

        Raises:
            ConflictingAccessionError: If any accession in the map already exists in the
                DB with a different file_id. All conflicts are collected before raising.
        """

    @abstractmethod
    async def get_accessions_by_file_ids(
        self, *, file_ids: set[UUID4]
    ) -> dict[UUID4, str]:
        """Query FileAccessionMapping records for the given file IDs.
        Returns a dict mapping file_id (UUID4) to accession (str).
        """

    @abstractmethod
    async def delete_mappings_for_file_ids(self, *, file_ids: set[UUID4]) -> None:
        """Delete FileAccessionMapping records for the given file IDs.

        Used when a ResearchDataUploadBox is deleted.
        """
