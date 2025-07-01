# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Port for the reverse transpiler core functionality."""

from abc import ABC, abstractmethod

from openpyxl import Workbook

from rts.models import StudyMetadata

__all__ = ["ReverseTranspilerPort"]


class ReverseTranspilerPort(ABC):
    """Provides functionality to convert study metadata from JSON files back into
    spreadsheet format.
    """

    class SheetNamingError(RuntimeError):
        """Raised when there is neither a configured nor default display value
        for a sheet name.
        """

        def __init__(self, sheet_name: str) -> None:
            """Initialize the error with a message."""
            message = f"No display value configured for sheet name '{sheet_name}'."
            super().__init__(message)

    class MetadataNotFoundError(RuntimeError):
        """Raised when the metadata cannot be retrieved from the database."""

        def __init__(self, study_accession: str) -> None:
            """Initialize the error with a message."""
            message = f"No workbook or metadata found for study accession '{study_accession}'."
            super().__init__(message)

    @abstractmethod
    async def upsert_metadata(self, *, study_metadata: StudyMetadata) -> None:
        """Upsert study metadata in the database.

        This will run the reverse transpilation process and store the resulting XLSX,
        even if the metadata already exists.
        """
        ...

    @abstractmethod
    async def retrieve_metadata(self, *, study_accession: str) -> StudyMetadata:
        """Retrieve study metadata from the DAO by its accession.

        Raises MetadataNotFoundError if the metadata does not exist for the
        given study accession.
        """
        ...

    @abstractmethod
    async def delete_metadata(self, *, study_accession: str) -> None:
        """Delete study metadata from the database by its accession.

        This method will always try to delete the associated workbook as well,
        regardless of whether the metadata exists or not.

        Does not raise an error if the metadata or workbook does not exist.
        """
        ...

    @abstractmethod
    def reverse_transpile(
        self,
        study_metadata: StudyMetadata,
    ) -> Workbook:
        """Convert StudyMetadata object to a workbook.

        Args:
        - `study_metadata`: The StudyMetadata instance to convert.

        Returns:
        - The metadata as an openpyxl Workbook.
        """
        ...

    @abstractmethod
    async def retrieve_workbook(self, *, study_accession: str) -> bytes:
        """Retrieve the workbook for a given study accession.

        Args:
        - `study_accession`: The accession of the study metadata to retrieve.

        Raises MetadataNotFoundError if the workbook does not exist.

        Returns:
        - The workbook as bytes.
        """
        ...
