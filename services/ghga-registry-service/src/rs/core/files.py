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

"""Core service logic"""

import logging

from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from rs.core.models import AltAccession, AltAccessionType, FileAccession
from rs.ports.inbound.files import FileControllerPort
from rs.ports.outbound.dao import AltAccessionDao

log = logging.getLogger(__name__)


class FileController(FileControllerPort):
    """Core implementation of Filename operations."""

    def __init__(self, *, alt_accession_dao: AltAccessionDao):
        self._alt_accession_dao = alt_accession_dao

    async def post_file_ids(
        self, *, study_pid: str, file_id_map: dict[FileAccession, UUID4]
    ) -> None:
        """Store file accession to internal file ID mappings."""
        for accession, file_id in file_id_map.items():
            # Upsert AltAccession with type FILE_ID
            alt = AltAccession(
                id=str(file_id),
                pid=accession,
                type=AltAccessionType.FILE_ID,
                created=now_utc_ms_prec(),
            )
            await self._alt_accession_dao.upsert(alt)
            log.info(
                "Upserted alt accession for internal file ID %s pointing to PID %s for study PID %s.",
                file_id,
                accession,
                study_pid,
            )
