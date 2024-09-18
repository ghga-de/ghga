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
"""Contains interfaces for public file information storage, retrieval and deletion."""

from abc import ABC, abstractmethod

import ghga_event_schemas.pydantic_ as event_schemas

from dins.core.models import DatasetFileInformation, FileInformation


class InformationServicePort(ABC):
    """Abstract baseclass for a service that handles storage and deletion of relevant
    metadata for files registered with the Internal File Registry service.
    """

    class MismatchingFileInformationAlreadyRegistered(RuntimeError):
        """Raised when the given file ID is already registered but the info doesn't match."""

        def __init__(self, *, file_id: str):
            message = f"Mismatching information for the file with ID {file_id} has already been registered."
            super().__init__(message)

    class DatasetNotFoundError(RuntimeError):
        """Raised when information for a given file ID is not registered."""

        def __init__(self, *, dataset_accession: str):
            message = f"Mapping for the dataset with ID {dataset_accession} is not registered."
            super().__init__(message)

    class InformationNotFoundError(RuntimeError):
        """Raised when information for a given file ID is not registered."""

        def __init__(self, *, file_id: str):
            message = f"Information for the file with ID {file_id} is not registered."
            super().__init__(message)

    @abstractmethod
    async def delete_dataset_information(self, dataset_id: str):
        """Delete dataset to file ID mapping when the corresponding dataset is deleted."""

    @abstractmethod
    async def delete_file_information(self, file_id: str):
        """Handle deletion requests for information associated with the given file ID."""

    @abstractmethod
    async def register_dataset_information(
        self, dataset: event_schemas.MetadataDatasetOverview
    ):
        """Extract dataset to file ID mapping and store it."""

    @abstractmethod
    async def register_file_information(
        self, file: event_schemas.FileInternallyRegistered
    ):
        """Store information for a file newly registered with the Internal File Registry."""

    @abstractmethod
    async def serve_dataset_information(
        self, dataset_id: str
    ) -> DatasetFileInformation:
        """Retrieve stored public information for the given dataset ID to be served by the API."""

    @abstractmethod
    async def serve_file_information(self, file_id: str) -> FileInformation:
        """Retrieve stored public information for the given file ID to be served by the API."""
