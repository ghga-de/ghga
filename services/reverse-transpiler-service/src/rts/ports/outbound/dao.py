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

"""DAO Port definition"""

from abc import ABC, abstractmethod

from hexkit.protocols.dao import Dao, ResourceNotFoundError
from openpyxl import Workbook

from rts.models import StudyMetadata

__all__ = ["MetadataDao", "ResourceNotFoundError", "WorkbookDaoPort"]

MetadataDao = Dao[StudyMetadata]


class WorkbookDaoPort(ABC):
    """Limited DAO for storing workbook data in the database."""

    @abstractmethod
    async def upsert(self, *, workbook: Workbook, study_accession: str) -> None:
        """Upsert the workbook for a given study accession.

        If the workbook already exists, it will be replaced.
        """
        ...

    @abstractmethod
    async def find(self, *, study_accession: str) -> bytes:
        """Retrieve the workbook for a given study accession.

        Raises `ResourceNotFoundError` if the workbook does not exist for the
        given study accession.
        """
        ...

    @abstractmethod
    async def delete(self, *, study_accession: str) -> None:
        """Delete the workbook for a given study accession.

        Does not raise an error if the workbook does not exist, as GridFS doesn't raise
        an error when trying to delete a non-existent file.
        """
        ...
