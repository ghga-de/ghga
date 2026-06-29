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

"""FileController implementation"""

import logging

from hexkit.protocols.dao import ResourceAlreadyExistsError
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from rs.core.models import PID, FileAccession
from rs.ports.inbound.files import FileControllerPort
from rs.ports.outbound.dao import FileAccessionDao

log = logging.getLogger(__name__)


class FileController(FileControllerPort):
    """Core implementation of file accession mapping and related operations."""

    def __init__(self, *, file_accession_dao: FileAccessionDao):
        self._file_accession_dao = file_accession_dao

    async def map_accessions_to_file_ids(
        self, *, study_id: str, file_id_map: dict[PID, UUID4]
    ) -> None:
        """Store file accession to internal file ID mappings.

        Each accession must already exist as an unmapped entry (no file ID) that was
        registered while tracking legacy searchable resources. Such entries are updated
        with the file ID, preserving their creation time. No new entries are created
        here: an accession with no entry yet is unknown. An accession that is already
        mapped to a different file ID, or that is attributed to a different study, is a
        conflict. Offending accessions are left untouched.

        Raises:
            UnknownAccessionError: If any accession in the map has no entry yet.
            ConflictingAccessionError: If any accession in the map already exists in the
                DB mapped to a different file ID or attributed to a different study.
            All offending accessions are collected before raising so callers receive
            the full picture in a single error.
        """
        existing_records = {
            record.pid: record
            async for record in self._file_accession_dao.find_all(
                mapping={"pid": {"$in": list(file_id_map)}}
            )
        }
        unknown_accessions = [
            accession for accession in file_id_map if accession not in existing_records
        ]
        if unknown_accessions:
            raise self.UnknownAccessionError(unknown_accessions=unknown_accessions)

        conflicting_accessions = [
            accession
            for accession, requested_file_id in file_id_map.items()
            if (
                (record := existing_records[accession]).file_id is not None
                and record.file_id != requested_file_id
            )
            or (record.study_id is not None and record.study_id != study_id)
        ]
        if conflicting_accessions:
            raise self.ConflictingAccessionError(
                conflicting_accessions=conflicting_accessions
            )

        for accession, file_id in file_id_map.items():
            # Update the existing unmapped entry, keeping its created time.
            file_accession = existing_records[accession].model_copy(
                update={
                    "file_id": file_id,
                    "study_id": study_id,
                    "mapped": now_utc_ms_prec(),
                }
            )
            await self._file_accession_dao.upsert(file_accession)
            log.info(
                "Upserted file accession mapping for file ID %s pointing to"
                " accession %s for study %s.",
                file_id,
                accession,
                study_id,
            )

    async def register_unmapped_accessions(
        self, *, study_id: str, accessions: set[PID]
    ) -> None:
        """Track each of the given accessions, creating an unmapped entry as needed.

        Used to record file accessions discovered in legacy searchable resources before
        they have been mapped to internal file IDs. For each accession:

        - if no entry exists yet, a new unmapped entry (no file ID) is created, carrying
          the study ID;
        - if an unmapped entry already exists but carries a different study ID (including
          none yet), the study ID is updated.

        Entries that are already mapped to a file ID, or that already carry the same study
        ID, are left untouched. Since only unmapped entries (no file ID) are written, none
        of these writes publish an outbox event.

        LEGACY: Only the searchable-resource consumer needs this. Remove once this service
        owns studies and experimental metadata itself.
        """
        for accession in accessions:
            try:
                await self._file_accession_dao.insert(
                    FileAccession(pid=accession, study_id=study_id)
                )
                log.info(
                    "Created unmapped file accession %s for study %s.",
                    accession,
                    study_id,
                )
            except ResourceAlreadyExistsError:
                record = await self._file_accession_dao.get_by_id(accession)
                if record.file_id is None and record.study_id != study_id:
                    await self._file_accession_dao.upsert(
                        record.model_copy(update={"study_id": study_id})
                    )
                    log.info(
                        "Updated file accession %s to study %s.",
                        accession,
                        study_id,
                    )

    async def get_study_ids_with_unmapped_accessions(self) -> set[str]:
        """Return the IDs of all studies that have at least one unmapped file accession.

        Queries the FileAccession records that have no file ID yet and collects the
        study IDs they are attributed to. Accessions without a study ID are skipped.
        """
        return {
            record.study_id
            async for record in self._file_accession_dao.find_all(
                mapping={"study_id": {"$ne": None}, "file_id": None}
            )
            if record.study_id is not None
        }

    async def get_accession_map(self, *, study_id: str) -> dict[str, UUID4 | None]:
        """Return the accession to file ID map for a study.

        Queries all FileAccession records attributed to the given study and returns a
        dict mapping each accession (str) to its internal file ID (UUID4), or None if
        the accession has not been mapped yet.
        """
        return {
            record.pid: record.file_id
            async for record in self._file_accession_dao.find_all(
                mapping={"study_id": study_id}
            )
        }

    async def get_accessions_by_file_ids(
        self, *, file_ids: set[UUID4]
    ) -> dict[UUID4, str]:
        """Query FileAccession records for the given file IDs.
        Returns a dict mapping file_id (UUID4) to accession (str).
        """
        result = {}
        async for record in self._file_accession_dao.find_all(
            mapping={"file_id": {"$in": list(file_ids)}}
        ):
            # The query only matches mapped records, so file_id is always set.
            if record.file_id is not None:
                result[record.file_id] = record.pid
        return result

    async def delete_mappings_for_file_ids(self, *, file_ids: set[UUID4]) -> None:
        """Delete FileAccessionMapping records for the given file IDs.

        Used when a ResearchDataUploadBox is deleted.
        """
        if not file_ids:
            return

        # Fetch the accessions, then delete each item.
        accessions_by_file_id = await self.get_accessions_by_file_ids(file_ids=file_ids)
        for file_id, accession in accessions_by_file_id.items():
            await self._file_accession_dao.delete(id_=accession)
            log.info(
                "Deleted file accession mapping for file ID %s (accession %s).",
                file_id,
                accession,
            )
