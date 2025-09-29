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

"""DAO implementation"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from io import BytesIO

from gridfs.asynchronous import AsyncGridFS
from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.providers.mongodb.provider import ConfiguredMongoClient, MongoDbConfig
from openpyxl import Workbook

from rts.models import StudyMetadata
from rts.ports.outbound.dao import MetadataDao, ResourceNotFoundError, WorkbookDaoPort

log = logging.getLogger(__name__)

__all__ = [
    "FILE_EXTENSION",
    "METADATA_COLLECTION",
    "WorkbookDao",
    "get_metadata_dao",
    "get_workbook_dao",
]

METADATA_COLLECTION = "metadata"
FILE_EXTENSION = ".xlsx"


async def get_metadata_dao(*, dao_factory: DaoFactoryProtocol) -> MetadataDao:
    """Construct a metadata DAO from the provided dao_factory"""
    return await dao_factory.get_dao(
        name=METADATA_COLLECTION,
        dto_model=StudyMetadata,
        id_field="study_accession",
    )


class WorkbookDao(WorkbookDaoPort):
    """Limited DAO for storing workbook data in the database."""

    def __init__(self, grid_fs: AsyncGridFS):
        """DO NOT CALL DIRECTLY! Use `get_workbook_dao` instead.

        Initialize the WorkbookDao with the provided AsyncGridFS instance.
        """
        self._grid_fs = grid_fs

    async def upsert(self, *, workbook: Workbook, study_accession: str) -> None:
        """Upsert the workbook for a given study accession.

        If the workbook already exists, it will be replaced.
        """
        # Convert the workbook to a bytestream
        workbook_bytestream = BytesIO()
        workbook.save(workbook_bytestream)
        workbook_bytestream.seek(0)

        # Delete the file if it already exists
        await self._grid_fs.delete(study_accession)

        # Insert new file
        await self._grid_fs.put(
            data=workbook_bytestream,
            _id=study_accession,
            filename=f"{study_accession}{FILE_EXTENSION}",  # e.g. my_accession.xlsx
        )
        log.debug("Workbook upserted for study accession: %s", study_accession)

    async def find(self, *, study_accession: str) -> bytes:
        """Retrieve the workbook for a given study accession.

        Raises `ResourceNotFoundError` if the workbook does not exist for the
        given study accession.
        """
        result = await self._grid_fs.find_one(study_accession)

        if result is None:
            raise ResourceNotFoundError(id_=study_accession)

        log.debug("Workbook found for study accession: %s", study_accession)

        return await result.read()

    async def delete(self, *, study_accession: str) -> None:
        """Delete the workbook for a given study accession.

        Does not raise an error if the workbook does not exist, as GridFS doesn't raise
        an error when trying to delete a non-existent file.
        """
        await self._grid_fs.delete(study_accession)
        log.debug("Workbook deleted for study accession: %s", study_accession)


@asynccontextmanager
async def get_workbook_dao(*, config: MongoDbConfig) -> AsyncGenerator[WorkbookDaoPort]:
    """Constructs the WorkbookDao with the provided MongoDB configuration."""
    async with ConfiguredMongoClient(config=config) as client:
        db = client[config.db_name]
        grid_fs = AsyncGridFS(db)
        yield WorkbookDao(grid_fs=grid_fs)
