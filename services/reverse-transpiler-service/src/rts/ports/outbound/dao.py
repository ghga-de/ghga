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

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from typing import Any

from gridfs import AsyncGridFSBucket, NoFile
from hexkit.protocols.dao import ResourceNotFoundError
from openpyxl import Workbook
from pymongo.asynchronous.database import AsyncDatabase

from rts.models import StudyMetadata

__all__ = [
    "GridFSDao",
    "GridFSDaoFactoryPort",
    "MetadataGridFSDaoPort",
    "ResourceNotFoundError",
    "WorkbookGridFSDaoPort",
]

log = logging.getLogger(__name__)


class GridFSDao[InputType: Any, OutputType: Any]:
    """A class that enables basic utilization of GridFS.

    This class could go into a library at some point.
    """

    class SerializationError(RuntimeError):
        """Raised when there's an error during data serialization"""

        def __init__(self, filename: str):
            msg = f"Failed to serialize data for filename {filename}"
            super().__init__(msg)

    class DeserializationError(RuntimeError):
        """Raised when there's an error during data deserialization"""

        def __init__(self, filename: str):
            msg = f"Failed to deserialize data for filename {filename}"
            super().__init__(msg)

    def __init__(
        self,
        *,
        db: AsyncDatabase,
        name: str,
        file_extension: str = "",
        serialize_fn: Callable[[InputType], bytes],
        deserialize_fn: Callable[[bytes], OutputType],
    ):
        """Initialize the WorkbookDao with the provided AsyncGridFS instance.

        Args:
            grid_fs: Instantiated AsyncGridFS object
            name: The name of the GridFSBucket to use -- analogous to collection name.
            file_extension: An optional file extension to use when storing the data.
            serialize_fn: A function that serializes the input data to bytes before
                storage in GridFS.
            deserialize_fn: A function that deserializes the data from bytes to the
                desired format.
        """
        self._bucket = AsyncGridFSBucket(db=db, bucket_name=name)
        self._serialize_fn = serialize_fn
        self._deserialize_fn = deserialize_fn
        if file_extension and not file_extension.startswith("."):
            file_extension = "." + file_extension
        self._file_extension = file_extension

    async def upsert(self, *, data: InputType, filename: str) -> None:
        """Upsert the data for a given filename (do not include extension).

        If a file with the same name already exists, it will be replaced.
        """
        # Serialize the data:
        try:
            serialized_data = self._serialize_fn(data)
        except Exception as err:
            error = self.SerializationError(filename)
            log.error(error, exc_info=True)
            raise error from err

        # Delete the file if it already exists
        with suppress(NoFile):
            await self._bucket.delete(filename)
            log.info("Found pre-existing file %s, overwriting.")

        # Insert new file
        await self._bucket.upload_from_stream_with_id(
            source=serialized_data,
            file_id=filename,
            filename=f"{filename}{self._file_extension}",
        )

    async def find(self, *, filename: str) -> OutputType:
        """Retrieve the file for a given filename (do not include file extension).

        Raises `ResourceNotFoundError` if the file does not exist for the
        given filename.
        """
        try:
            result = await self._bucket.open_download_stream(filename)
        except NoFile as err:
            raise ResourceNotFoundError(id_=filename) from err

        serialized_data = await result.read()
        try:
            deserialized_data = self._deserialize_fn(serialized_data)
        except Exception as err:
            error = self.DeserializationError(filename)
            log.error(error, exc_info=True)
            raise error from err
        return deserialized_data

    async def find_all(self) -> AsyncIterator[OutputType]:
        """Returns an iterator of all files in the bucket."""
        async for file in self._bucket.find():
            file_bytes = await file.read()
            try:
                deserialized_data = self._deserialize_fn(file_bytes)
            except Exception as err:
                error = self.DeserializationError(file.filename)
                log.error(error, exc_info=True)
                raise error from err
            yield deserialized_data

    async def delete(self, *, filename: str) -> None:
        """Delete the file for a given filename (do not include the extension).

        Raises a ResourceNotFoundError if the file doesn't exist.
        """
        try:
            await self._bucket.delete(filename)
        except NoFile as err:
            raise ResourceNotFoundError(id_=filename) from err


WorkbookGridFSDaoPort = GridFSDao[Workbook, bytes]
MetadataGridFSDaoPort = GridFSDao[StudyMetadata, StudyMetadata]


class GridFSDaoFactoryPort(ABC):
    """Port definition of a factory that produces objects able to interact with GridFS"""

    @abstractmethod
    def get_metadata_dao(self) -> MetadataGridFSDaoPort:
        """Return a MetadataDaoPort instance"""

    @abstractmethod
    def get_workbook_dao(self) -> WorkbookGridFSDaoPort:
        """Return a WorkbookDaoPort instance"""
