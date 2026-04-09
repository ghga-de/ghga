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
"""Contains logic for public file information storage, retrieval and deletion."""

import logging
from contextlib import suppress

from ghga_event_schemas.pydantic_ import (
    FileAccessionMapping,
    FileInternallyRegistered,
    MetadataDatasetOverview,
)
from hexkit.protocols.dao import NoHitsFoundError, ResourceNotFoundError
from pydantic import UUID4

from dins.core.models import (
    DatasetFileAccessions,
    DatasetFileInformation,
    FileAccession,
    FileInformation,
    PendingFileInfo,
)
from dins.ports.inbound.dao import (
    DatasetDaoPort,
    FileAccessionMapDaoPort,
    FileInformationDaoPort,
    PendingFileInfoDaoPort,
)
from dins.ports.inbound.information_service import InformationServicePort

log = logging.getLogger(__name__)


class InformationService(InformationServicePort):
    """A service that handles storage and deletion of relevant metadata for files
    registered with the Internal File Registry service.
    """

    def __init__(
        self,
        *,
        accession_map_dao: FileAccessionMapDaoPort,
        dataset_dao: DatasetDaoPort,
        file_information_dao: FileInformationDaoPort,
        pending_file_info_dao: PendingFileInfoDaoPort,
    ):
        self._accession_map_dao = accession_map_dao
        self._dataset_dao = dataset_dao
        self._file_information_dao = file_information_dao
        self._pending_file_info_dao = pending_file_info_dao

    async def register_dataset_information(self, dataset: MetadataDatasetOverview):
        """Extract dataset to file accession mapping and store it."""
        dataset_accession = dataset.accession
        file_accessions = [file.accession for file in dataset.files]

        dataset_file_accessions = DatasetFileAccessions(
            accession=dataset_accession, file_accessions=file_accessions
        )

        await self._dataset_dao.upsert(dataset_file_accessions)

    async def delete_dataset_information(self, dataset_id: str):
        """Delete dataset to file accession mapping when the corresponding dataset is deleted."""
        try:
            await self._dataset_dao.delete(dataset_id)
        except ResourceNotFoundError:
            log.info(
                "Mapping for dataset %s does not exist, presumed already deleted.",
                dataset_id,
            )
        else:
            log.info("Successfully deleted mapping for dataset %s.", dataset_id)

    async def register_file_information(self, file_information: FileInformation):
        """Store information for a file newly registered with the Internal File Registry."""
        accession = file_information.accession

        try:
            existing_information = await self._file_information_dao.get_by_id(accession)
        except ResourceNotFoundError:
            await self._file_information_dao.insert(file_information)
            log.debug("Successfully inserted information for file %s.", accession)
        else:
            log.debug("Found existing information for file %s.", accession)
            # Log and raise if information to be inserted is a mismatch
            if existing_information != file_information:
                information_exists = self.MismatchingFileInformationAlreadyRegistered(
                    accession=accession
                )
                log.error(information_exists)
                raise information_exists

    async def delete_file_information(self, file_id: UUID4):
        """Delete FileInformation for the given file ID.

        If no accession map is found for the file ID, logs and returns early.
        If the accession map exists but no FileInformation is stored, logs and returns.
        """
        try:
            accession_map = await self._accession_map_dao.find_one(
                mapping={"file_id": file_id}
            )
        except NoHitsFoundError:
            log.info(
                "No accession map found for %s, presumed already deleted.", file_id
            )
            return

        try:
            accession = accession_map.accession
            await self._file_information_dao.delete(accession)
        except ResourceNotFoundError:
            log.info(
                "Information for file with accession %s does not exist.", accession
            )
        else:
            log.info(
                "Successfully deleted entries for file with accession %s.", accession
            )

    async def handle_file_internally_registered(
        self, *, file: FileInternallyRegistered
    ) -> None:
        """Decide how to handle a new file registration.

        If a corresponding FileAccessionMap already exists, merge and store FileInformation.
        If not, temporarily store the essential fields as a PendingFileInfo instance.
        """
        try:
            accession_map = await self._accession_map_dao.find_one(
                mapping={"file_id": file.file_id}
            )
        except NoHitsFoundError:
            pending = PendingFileInfo(
                file_id=file.file_id,
                decrypted_size=file.decrypted_size,
                decrypted_sha256=file.decrypted_sha256,
                storage_alias=file.storage_alias,
            )
            await self.store_pending_file_info(pending=pending)
        else:
            file_information = FileInformation(
                accession=accession_map.accession,
                size=file.decrypted_size,
                sha256_hash=file.decrypted_sha256,
                storage_alias=file.storage_alias,
            )
            await self.register_file_information(file_information=file_information)

    async def store_pending_file_info(self, *, pending: PendingFileInfo) -> None:
        """Store a PendingFileInfo record. Duplicates are ignored.

        Raises MismatchingPendingFileInfoExists if differing data is already stored.
        """
        try:
            existing_pending = await self._pending_file_info_dao.get_by_id(
                pending.file_id
            )
        except ResourceNotFoundError:
            await self._pending_file_info_dao.insert(pending)
            log.info("Stored pending file info for file_id %s.", pending.file_id)
        else:
            if existing_pending == pending:
                log.info(
                    "Duplicate pending file info received for file_id %s, skipping.",
                    pending.file_id,
                )
            else:
                mismatch = self.MismatchingPendingFileInfoExists(
                    file_id=pending.file_id
                )
                log.error(mismatch)
                raise mismatch

    async def store_accession_map(self, *, accession_map: FileAccessionMapping) -> None:
        """Upsert an accession map, then merge any waiting PendingFileInfo into FileInformation.

        Raises MismatchingFileInformationAlreadyRegistered if the accession is already mapped
        to a different file_id and a FileInformation record already exists for this accession.
        Ignores duplicates. After upserting, triggers a merge if a PendingFileInfo
        record exists for the associated file_id.
        """
        accession = accession_map.accession
        try:
            existing_map = await self._accession_map_dao.get_by_id(accession)
        except ResourceNotFoundError:
            existing_map = None

        # Handle potential inconsistencies
        if existing_map is not None and accession_map != existing_map:
            with suppress(ResourceNotFoundError):
                await self._file_information_dao.get_by_id(accession_map.accession)
                log.error(
                    "FileInformation is already registered for accession %s, but this"
                    + " accession map is different from what is stored already.",
                    accession,
                    extra={
                        "accession": accession,
                        "currently_mapped_file_id": existing_map.file_id,
                        "new_file_id": accession_map.file_id,
                    },
                )
                raise self.MismatchingFileInformationAlreadyRegistered(
                    accession=accession
                )
        # If it already exists and differs, this is fine as long as no file is
        #  already registered
        await self._accession_map_dao.upsert(accession_map)
        log.info(
            "Upserted accession map for accession %s, file ID %s.",
            accession_map.accession,
            accession_map.file_id,
        )

        # Now check to see if the corresponding PendingFileInfo is already in the DB.
        #  We do this even if the mapping is a duplicate, as it provides a path for
        #  error recovery if the two components make it to the DB without being merged.
        try:
            pending = await self._pending_file_info_dao.get_by_id(accession_map.file_id)
        except ResourceNotFoundError:
            log.info(
                "Accession map received for %s but still waiting for FileInternallyRegistered event.",
                accession,
            )
            return

        # PendingFileInfo exists, register the FileInformation
        file_information = FileInformation(
            accession=accession_map.accession,
            size=pending.decrypted_size,
            sha256_hash=pending.decrypted_sha256,
            storage_alias=pending.storage_alias,
        )
        log.info(
            "Merged accession map for %s with file info for %s, registering FileInformation.",
            accession,
            accession_map.file_id,
        )
        await self.register_file_information(file_information=file_information)

        # Delete the pending file info. If this doesn't get done, the data will linger
        #  but otherwise should not cause problems.
        await self._pending_file_info_dao.delete(accession_map.file_id)
        log.info(
            "Merged pending file info for file_id %s with accession %s.",
            accession_map.file_id,
            accession_map.accession,
        )

    async def delete_accession_map(self, *, accession: str) -> None:
        """Delete the accession map entry identified by the given accession.

        No error is raised if no entry exists for the accession.
        """
        try:
            await self._accession_map_dao.delete(accession)
        except ResourceNotFoundError:
            log.info("Accession map for accession %s does not exist.", accession)
        else:
            log.info("Accession mapping deleted for accession %s.", accession)

    async def serve_dataset_information(
        self, dataset_id: str
    ) -> DatasetFileInformation:
        """Retrieve stored public information for the given dataset ID to be served by the API."""
        try:
            dataset = await self._dataset_dao.get_by_id(dataset_id)
            log.debug("Found mapping for dataset %s.", dataset_id)
        except ResourceNotFoundError as error:
            dataset_not_found = self.DatasetNotFoundError(dataset_accession=dataset_id)
            log.debug(dataset_not_found)
            raise dataset_not_found from error

        file_accessions_mapping = {"accession": {"$in": dataset.file_accessions}}

        file_informations = [
            single_file_information
            async for single_file_information in self._file_information_dao.find_all(
                mapping=file_accessions_mapping
            )
        ]

        matched_accessions = {
            file_information.accession for file_information in file_informations
        }
        missing_accessions = set(dataset.file_accessions) - matched_accessions

        log.debug(
            "%s: File information found: [%s]; Missing: [%s]",
            dataset_id,
            matched_accessions,
            missing_accessions,
        )

        file_accessions = [
            FileAccession(accession=accession) for accession in missing_accessions
        ]

        combined = sorted(
            file_informations + file_accessions, key=lambda x: x.accession
        )

        return DatasetFileInformation(accession=dataset_id, file_information=combined)

    async def serve_file_information(self, accession: str) -> FileInformation:
        """Retrieve stored public information for the given file accession to be served by the API."""
        try:
            file_information = await self._file_information_dao.get_by_id(accession)
            log.debug("Found information for file %s.", accession)
        except ResourceNotFoundError as error:
            information_not_found = self.InformationNotFoundError(accession=accession)
            log.debug(information_not_found)
            raise information_not_found from error

        return file_information
