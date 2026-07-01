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
"""GHGA Registry implementation"""

from hexkit.protocols.dao import ResourceNotFoundError

from rs.core.models import Study
from rs.ports.inbound.files import FileControllerPort
from rs.ports.inbound.legacy_resources import LegacyResourceManagerPort
from rs.ports.inbound.rdub_manager import RDUBManagerPort
from rs.ports.inbound.registry import RegistryPort
from rs.ports.outbound.dao import StudyDao


class Registry(RegistryPort):
    """Top-level class linking all constituent registry operations"""

    def __init__(
        self,
        *,
        rdub_manager: RDUBManagerPort,
        legacy_resource_manager: LegacyResourceManagerPort,
        study_dao: StudyDao,
        file_controller: FileControllerPort,
    ) -> None:
        self._rdub_manager = rdub_manager
        self._legacy_resource_manager = legacy_resource_manager
        self._study_dao = study_dao
        # Owns file accession / file ID mappings; exposed via the file_controller property
        # and used to resolve which studies still have unmapped file accessions.
        self._file_controller = file_controller

    @property
    def rdub_manager(self) -> RDUBManagerPort:
        """The RDUBManager component."""
        return self._rdub_manager

    @property
    def legacy_resource_manager(self) -> LegacyResourceManagerPort:
        """The LegacyResourceManager component."""
        return self._legacy_resource_manager

    @property
    def file_controller(self) -> FileControllerPort:
        """The FileController component."""
        return self._file_controller

    async def get_study(self, study_id: str) -> Study:
        """Get a single study by its ID."""
        try:
            return await self._study_dao.get_by_id(study_id)
        except ResourceNotFoundError as err:
            raise self.StudyNotFoundError(study_id=study_id) from err

    async def get_studies(self, *, with_unmapped_files: bool = False) -> list[Study]:
        """Get the list of all studies, sorted by study ID."""
        mapping: dict = {}
        if with_unmapped_files:
            study_ids = (
                await self._file_controller.get_study_ids_with_unmapped_accessions()
            )
            if not study_ids:
                return []
            mapping = {"id": {"$in": list(study_ids)}}
        return await self._study_dao.find_all(mapping=mapping, sort=["id"]).to_list()
