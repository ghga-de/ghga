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


"""The main upload handling logic."""

from collections.abc import Sequence

from ucs.core import models
from ucs.ports.inbound.file_service import (
    UPDATABLE_METADATA_FIELDS,
    FileMetadataServicePort,
)
from ucs.ports.outbound.dao import DaoCollectionPort, ResourceNotFoundError


def _get_metadata_diff(a: models.FileMetadata, b: models.FileMetadata) -> set[str]:
    """Check which fields differ between the metadata provided in a and b."""
    a_dict = a.model_dump()
    b_dict = b.model_dump()

    return {field for field in a_dict if a_dict[field] != b_dict[field]}


class FileMetadataServive(FileMetadataServicePort):
    """Implementation of a service handling file metata."""

    def __init__(self, *, daos: DaoCollectionPort):
        """Initialize class instance with configs and outbound adapter objects."""
        self._daos = daos

    @classmethod
    def _assert_update_allowed(
        cls,
        *,
        updated_metadata: models.FileMetadata,
        existing_metadata: models.FileMetadata,
    ) -> None:
        """Checks whether only fields that are allowed to be changed are affected by the
        proposed update. Raises an InvalidFileMetadataUpdateError otherwise.
        """
        affected_fields = _get_metadata_diff(updated_metadata, existing_metadata)
        not_allowed_field = affected_fields.difference(UPDATABLE_METADATA_FIELDS)

        if not_allowed_field:
            raise cls.InvalidFileMetadataUpdateError(
                file_id=existing_metadata.file_id, invalid_fields=not_allowed_field
            )

    async def _insert_new(self, file: models.FileMetadataUpsert) -> None:
        """Create a metadata entry for a new file."""
        full_metadata = models.FileMetadata(**file.model_dump(), latest_upload_id=None)
        await self._daos.file_metadata.insert(full_metadata)

    async def _update_existing(
        self, update: models.FileMetadataUpsert, existing_metadata: models.FileMetadata
    ) -> None:
        """Update the metadata for an existing file entry.
        Please note: not all metadata fields may be updated.

        Raises:
            InvalidFileMetadataUpdateError:
                When trying to update a metadata field, that can only be set on
                creation.
        """
        full_metadata = models.FileMetadata(
            **update.model_dump(), latest_upload_id=existing_metadata.latest_upload_id
        )

        self._assert_update_allowed(
            updated_metadata=full_metadata, existing_metadata=existing_metadata
        )

        await self._daos.file_metadata.update(full_metadata)

    async def upsert_one(self, file: models.FileMetadataUpsert) -> None:
        """Register a new file or update the metadata for an existing one.

        Raises:
            InvalidFileMetadataUpdateError:
                When trying to update a metadata field, that can only be set on
                creation.
        """
        # check if the file already exist:
        try:
            existing_metadata = await self._daos.file_metadata.get_by_id(file.file_id)
        except ResourceNotFoundError:
            # there is no entry for that file in the database, yet => create it:
            await self._insert_new(file)
        else:
            # there is an existing entry that might require updates:
            await self._update_existing(
                update=file, existing_metadata=existing_metadata
            )

    async def upsert_multiple(self, files: Sequence[models.FileMetadataUpsert]) -> None:
        """Registers new files or updates the metadata for existing ones.

        Raises:
            InvalidFileMetadataUpdateError:
                When trying to update a metadata field, that can only be set on
                creation.
        """
        for file in files:
            await self.upsert_one(file)

    async def get_by_id(
        self,
        file_id: str,
    ) -> models.FileMetadata:
        """
        Get metadata on the filed with the provided ID.

        Raises:
            UnknownFileError:
                When a file with the corresponding ID does not exist.
        """
        try:
            return await self._daos.file_metadata.get_by_id(file_id)
        except ResourceNotFoundError as error:
            raise self.FileUnknownError(file_id=file_id) from error
