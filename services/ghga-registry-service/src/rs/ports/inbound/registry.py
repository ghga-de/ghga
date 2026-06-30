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

"""Defines the main GHGA Registry Service inbound port."""

from abc import ABC, abstractmethod

from rs.core.models import Study
from rs.ports.inbound.files import FileControllerPort
from rs.ports.inbound.legacy_resources import LegacyResourceManagerPort
from rs.ports.inbound.rdub_manager import RDUBManagerPort


class RegistryPort(ABC):
    """Inbound port defining all operations of the GHGA Registry Service."""

    class StudyNotFoundError(RuntimeError):
        """Raised when a study with the given ID could not be found."""

        def __init__(self, *, study_id: str) -> None:
            self.study_id = study_id
            super().__init__(f"Study with ID {study_id} not found.")

    @property
    @abstractmethod
    def rdub_manager(self) -> RDUBManagerPort:
        """The RDUBManager component."""
        ...

    @property
    @abstractmethod
    def legacy_resource_manager(self) -> LegacyResourceManagerPort:
        """The LegacyResourceManager component."""
        ...

    @property
    @abstractmethod
    def file_controller(self) -> FileControllerPort:
        """The FileController component."""
        ...

    @abstractmethod
    async def get_study(self, study_id: str) -> Study:
        """Get a single study by its ID.

        Raises:
            StudyNotFoundError: If no study with the given ID exists.
        """
        ...

    @abstractmethod
    async def get_studies(self, *, with_unmapped_files: bool = False) -> list[Study]:
        """Get the list of all studies, sorted by study ID.

        Args:
            with_unmapped_files:
                If True, only return studies that have at least one associated file
                accession that has not been mapped to an internal file ID yet.
        """
        ...
