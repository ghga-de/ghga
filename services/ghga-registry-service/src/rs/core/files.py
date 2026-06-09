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

from ghga_event_schemas.pydantic_ import FileAccessionMapping
from pydantic import UUID4

from rs.core.models import FileAccession
from rs.ports.inbound.files import FileControllerPort
from rs.ports.outbound.dao import FileAccessionMappingDao

log = logging.getLogger(__name__)


class FileController(FileControllerPort):
    """Core implementation of file accession mapping and related operations."""

    def __init__(self, *, file_accession_mapping_dao: FileAccessionMappingDao):
        self._file_accession_mapping_dao = file_accession_mapping_dao

    async def post_file_ids(
        self, *, study_id: str, file_id_map: dict[FileAccession, UUID4]
    ) -> None:
        """Store file accession to internal file ID mappings.

        Raises:
            ConflictingAccessionError: If any accession in the map already exists in the
                DB with a different file_id. All conflicts are collected before raising
                so callers receive the full picture in a single error.
        """
        existing_mappings = {
            record.accession: record.file_id
            async for record in self._file_accession_mapping_dao.find_all(
                mapping={"accession": {"$in": list(file_id_map)}}
            )
        }
        conflicting_accessions = [
            accession
            for accession, requested_file_id in file_id_map.items()
            if existing_mappings.get(accession, requested_file_id) != requested_file_id
        ]

        if conflicting_accessions:
            raise self.ConflictingAccessionError(
                conflicting_accessions=conflicting_accessions
            )

        for accession, file_id in file_id_map.items():
            mapping = FileAccessionMapping(file_id=file_id, accession=accession)
            await self._file_accession_mapping_dao.upsert(mapping)
            log.info(
                "Upserted file accession mapping for file ID %s pointing to"
                " accession %s for study %s.",
                file_id,
                accession,
                study_id,
            )

    async def get_accessions_by_file_ids(
        self, *, file_ids: set[UUID4]
    ) -> dict[UUID4, str]:
        """Query FileAccessionMapping records for the given file IDs.
        Returns a dict mapping file_id (UUID4) to accession (str).
        """
        result = {}
        async for record in self._file_accession_mapping_dao.find_all(
            mapping={"file_id": {"$in": list(file_ids)}}
        ):
            result[record.file_id] = record.accession
        return result
