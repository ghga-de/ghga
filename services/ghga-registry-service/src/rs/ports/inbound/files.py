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

from rs.core.models import PID


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

    class UnknownAccessionError(RuntimeError):
        """Raised when a request maps accessions that have no (unmapped) entry yet.

        Accessions must first be registered (as unmapped entries) from the searchable
        resources before they can be mapped to a file ID.
        """

        def __init__(self, *, unknown_accessions: list[str]) -> None:
            self.unknown_accessions = unknown_accessions
            accessions = ", ".join(unknown_accessions)
            super().__init__(f"Unknown accessions: {accessions}")

    @abstractmethod
    async def map_accessions_to_file_ids(
        self, *, study_id: str, file_id_map: dict[PID, UUID4]
    ) -> None:
        """Store file accession to internal file ID mappings.

        Each accession must already exist as an unmapped entry (registered while
        tracking legacy searchable resources); that entry is updated with the file ID.
        No new accession entries are created here.

        Raises:
            ConflictingAccessionError: If any accession in the map already exists in the
                DB mapped to a different file ID or attributed to a different study.
            UnknownAccessionError: If any accession in the map has no entry yet.
            All offending accessions are collected before raising.
        """

    @abstractmethod
    async def register_unmapped_accessions(
        self, *, study_id: str, accessions: set[PID]
    ) -> None:
        """Ensure a FileAccession entry exists for each of the given accessions.

        Creates a new unmapped entry (no file ID) for unknown accessions and backfills
        the study ID onto existing entries that do not have one yet. Used to track file
        accessions discovered in legacy searchable resources.
        """

    @abstractmethod
    async def get_study_ids_with_unmapped_accessions(self) -> set[str]:
        """Return the IDs of all studies that have at least one unmapped file accession.

        An accession is unmapped while it has no internal UUID4 file ID yet. Accessions that
        carry no study ID are ignored, as they cannot be attributed to a study.
        """

    @abstractmethod
    async def get_accession_map(self, *, study_id: str) -> dict[str, UUID4 | None]:
        """Return the accession to file ID map for a study.

        Queries all FileAccession records attributed to the given study and returns a
        dict mapping each accession (str) to its internal file ID (UUID4), or None if
        the accession has not been mapped yet.
        """

    @abstractmethod
    async def get_accessions_by_file_ids(
        self, *, file_ids: set[UUID4]
    ) -> dict[UUID4, str]:
        """Query FileAccession records for the given file IDs.
        Returns a dict mapping file_id (UUID4) to accession (str).
        """

    @abstractmethod
    async def delete_mappings_for_file_ids(self, *, file_ids: set[UUID4]) -> None:
        """Delete FileAccessionMapping records for the given file IDs.

        Used when a ResearchDataUploadBox is deleted.
        """
