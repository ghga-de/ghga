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
"""Contains interfaces for public file information storage, retrieval and deletion."""

from abc import ABC, abstractmethod

import ghga_event_schemas.pydantic_ as event_schemas
from pydantic import UUID4

from dins.core.models import (
    DatasetFileInformation,
    FileAccessionMap,
    FileInformation,
    FileInternallyRegistered,
    PendingFileInfo,
)


class InformationServicePort(ABC):
    """Abstract baseclass for a service that handles storage and deletion of relevant
    metadata for files registered with the Internal File Registry service.
    """

    class MismatchingFileInformationAlreadyRegistered(RuntimeError):
        """Raised when the given accession is already registered but the info doesn't match."""

        def __init__(self, *, accession: str):
            message = f"Mismatching information for the file with accession {accession} has already been registered."
            super().__init__(message)

    class MismatchingPendingFileInfoExists(RuntimeError):
        """Raised when differing pending file info is already stored for the given file ID."""

        def __init__(self, *, file_id: UUID4):
            message = f"Mismatching pending file info for file ID {file_id} has already been stored."
            super().__init__(message)

    class DatasetNotFoundError(RuntimeError):
        """Raised when information for a given dataset accession is not registered."""

        def __init__(self, *, dataset_accession: str):
            message = f"Mapping for the dataset with accession {dataset_accession} is not registered."
            super().__init__(message)

    class InformationNotFoundError(RuntimeError):
        """Raised when information for a given file accession is not registered."""

        def __init__(self, *, accession: str):
            message = f"Information for the file with accession {accession} is not registered."
            super().__init__(message)

    @abstractmethod
    async def register_dataset_information(
        self, dataset: event_schemas.MetadataDatasetOverview
    ) -> None:
        """Extract dataset to file accession mapping and store it."""

    @abstractmethod
    async def delete_dataset_information(self, dataset_id: str) -> None:
        """Delete dataset to file accession mapping when the corresponding dataset is deleted."""

    @abstractmethod
    async def register_file_information(
        self, file_information: FileInformation
    ) -> None:
        """Store information for a file newly registered with the Internal File Registry."""

    @abstractmethod
    async def delete_file_information(self, file_id: UUID4) -> None:
        """Delete FileInformation for the given file ID.

        If no accession map is found for the file ID, logs and returns early.
        If the accession map exists but no FileInformation is stored, logs and returns.
        """

    @abstractmethod
    async def handle_file_internally_registered(
        self, *, file: FileInternallyRegistered
    ) -> None:
        """Decide how to handle a new file registration.

        If a corresponding FileAccessionMap already exists, merge and store FileInformation.
        If not, temporarily store the essential fields as a PendingFileInfo instance.
        """

    @abstractmethod
    async def store_pending_file_info(self, *, pending: PendingFileInfo) -> None:
        """Store a PendingFileInfo record. Duplicates are ignored.

        Raises MismatchingPendingFileInfoExists if differing data is already stored.
        """

    @abstractmethod
    async def store_accession_map(self, *, accession_map: FileAccessionMap) -> None:
        """Upsert an accession map, then merge any waiting PendingFileInfo into FileInformation.

        Raises MismatchingFileInformationAlreadyRegistered if the accession is already mapped
        to a different file_id and a FileInformation record already exists for this accession.
        Ignores duplicates. After upserting, triggers a merge if a PendingFileInfo
        record exists for the associated file_id.
        """

    @abstractmethod
    async def delete_accession_map(self, *, accession: str) -> None:
        """Delete the accession map entry identified by the given accession.

        No error is raised if no entry exists for the accession.
        """

    @abstractmethod
    async def serve_dataset_information(
        self, dataset_id: str
    ) -> DatasetFileInformation:
        """Retrieve stored public information for the given dataset ID to be served by the API."""

    @abstractmethod
    async def serve_file_information(self, accession: str) -> FileInformation:
        """Retrieve stored public information for the given file accession to be served by the API."""
