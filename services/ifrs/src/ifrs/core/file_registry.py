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

"""Main business-logic of this service"""

import logging
import uuid
from contextlib import suppress

from ghga_service_commons.utils.multinode_storage import ObjectStorages

from ifrs.config import Config
from ifrs.core import models
from ifrs.ports.inbound.file_registry import FileRegistryPort
from ifrs.ports.outbound.dao import FileMetadataDaoPort, ResourceNotFoundError
from ifrs.ports.outbound.event_pub import EventPublisherPort

log = logging.getLogger(__name__)


class FileRegistry(FileRegistryPort):
    """A service that manages a registry files stored on a permanent object storage."""

    def __init__(
        self,
        *,
        file_metadata_dao: FileMetadataDaoPort,
        event_publisher: EventPublisherPort,
        object_storages: ObjectStorages,
        config: Config,
    ):
        """Initialize with essential config params and outbound adapters."""
        self._event_publisher = event_publisher
        self._file_metadata_dao = file_metadata_dao
        self._object_storages = object_storages
        self._config = config

    async def _is_file_registered(
        self, *, file_without_object_id: models.FileMetadataBase
    ) -> bool:
        """Checks if the specified file is already registered. There are three possible
        outcomes:
            - Yes, the file has been registered with metadata that is identical to the
              provided one => returns `True`
            - Yes, however, the metadata differs => raises self.FileUpdateError
            - No, the file has not been registered, yet => returns `False`
        """
        try:
            registered_file = await self._file_metadata_dao.get_by_id(
                file_without_object_id.file_id
            )
        except ResourceNotFoundError:
            return False

        # object ID is a UUID generated upon registration, so cannot compare those
        registered_file_without_object_id = registered_file.model_dump(
            exclude={"object_id"}
        )

        if file_without_object_id.model_dump() == registered_file_without_object_id:
            return True

        raise self.FileUpdateError(file_id=file_without_object_id.file_id)

    async def register_file(
        self,
        *,
        file_without_object_id: models.FileMetadataBase,
        staging_object_id: str,
        staging_bucket_id: str,
    ) -> None:
        """Registers a file and moves its content from the staging into the permanent
        storage. If the file with that exact metadata has already been registered,
        nothing is done.

        Args:
            file_without_object_id: metadata on the file to register.
            staging_object_id:
                The S3 object ID for the staging bucket.
            staging_bucket_id:
                The S3 bucket ID for staging.

        Raises:
            self.FileContentNotInStagingError:
                When the file content is not present in the storage staging.
            ValueError:
                When the configuration for the storage alias is not found.
            self.CopyOperationError:
                When an error occurs while attempting to copy the object to the
                permanent storage bucket.
        """
        storage_alias = file_without_object_id.storage_alias

        try:
            permanent_bucket_id, object_storage = self._object_storages.for_alias(
                storage_alias
            )
        except KeyError as error:
            alias_not_configured = ValueError(
                f"Storage alias '{storage_alias}' not configured."
            )
            log.critical(alias_not_configured, extra={"storage_alias": storage_alias})
            raise alias_not_configured from error

        try:
            if await self._is_file_registered(
                file_without_object_id=file_without_object_id
            ):
                # There is nothing to do:
                log.info(
                    "File with ID '%s' is already registered.",
                    file_without_object_id.file_id,
                )
                return
        except self.FileUpdateError as error:
            # trying to re-register with different metadata should not crash the consumer
            # this is not a service internal inconsistency and would cause unnecessary
            # crashes on additional consumption attempts
            log.error(error)
            return

        # Generate & assign object ID to metadata
        log.info(
            "File with ID '%s' is not yet registered. Generating object ID.",
            file_without_object_id.file_id,
        )
        object_id = str(uuid.uuid4())
        file = models.FileMetadata(
            **file_without_object_id.model_dump(), object_id=object_id
        )

        # Make sure the object exists in the source bucket (staging)
        if not await object_storage.does_object_exist(
            bucket_id=staging_bucket_id, object_id=staging_object_id
        ):
            content_not_in_staging = self.FileContentNotInStagingError(
                file_id=file_without_object_id.file_id
            )
            log.error(
                content_not_in_staging,
                extra={"file_id": file_without_object_id.file_id},
            )
            raise content_not_in_staging

        # Copy the file from staging to permanent storage
        try:
            await object_storage.copy_object(
                source_bucket_id=staging_bucket_id,
                source_object_id=staging_object_id,
                dest_bucket_id=permanent_bucket_id,
                dest_object_id=object_id,
            )
        except object_storage.ObjectAlreadyExistsError:
            # the content is already where it should go, there is nothing to do
            log.info(
                "Object corresponding to file ID '%s' is already in permanent storage.",
                file_without_object_id.file_id,
            )
            return
        except Exception as exc:
            # Irreconcilable object error -- event needs investigation
            obj_error = self.CopyOperationError(
                file_id=file_without_object_id.file_id,
                dest_bucket_id=permanent_bucket_id,
                exc_text=str(exc),
            )
            log.critical(obj_error)
            raise obj_error from exc

        # Log the registration and publish an event
        log.info("Inserting file with file ID '%s'.", file.file_id)
        await self._file_metadata_dao.insert(file)

        await self._event_publisher.file_internally_registered(
            file=file, bucket_id=permanent_bucket_id
        )

    async def stage_registered_file(
        self,
        *,
        file_id: str,
        decrypted_sha256: str,
        outbox_object_id: str,
        outbox_bucket_id: str,
    ) -> None:
        """Stage a registered file to the outbox.

        Args:
            file_id:
                The identifier of the file.
            decrypted_sha256:
                The checksum of the decrypted content. This is used to make sure that
                this service and the outside client are talking about the same file.
            outbox_object_id:
                The S3 object ID for the outbox bucket.
            outbox_bucket_id:
                The S3 bucket ID for the outbox.

        Raises:
            self.ChecksumMismatchError:
                When the provided checksum did not match the expectations.
            self.FileInRegistryButNotInStorageError:
                When encountering inconsistency between the registry (the database) and
                the permanent storage. This is an internal service error, which should
                not happen, and not the fault of the client.
            self.CopyOperationError:
                When an error occurs while attempting to copy the object to the outbox.
        """
        try:
            file = await self._file_metadata_dao.get_by_id(file_id)
        except ResourceNotFoundError:
            file_not_in_registry_error = self.FileNotInRegistryError(file_id=file_id)
            log.error(file_not_in_registry_error, extra={"file_id": file_id})
            return

        if decrypted_sha256 != file.decrypted_sha256:
            checksum_error = self.ChecksumMismatchError(
                file_id=file_id,
                provided_checksum=decrypted_sha256,
                expected_checksum=file.decrypted_sha256,
            )
            log.error(
                checksum_error,
                extra={
                    "file_id": file_id,
                    "provided_checksum": decrypted_sha256,
                    "expected_checksum": file.decrypted_sha256,
                },
            )
            raise checksum_error

        permanent_bucket_id, object_storage = self._object_storages.for_alias(
            file.storage_alias
        )

        # Make sure the file exists in permanent storage before trying to copy it
        if not await object_storage.does_object_exist(
            bucket_id=permanent_bucket_id, object_id=file.object_id
        ):
            not_in_storage_error = self.FileInRegistryButNotInStorageError(
                file_id=file_id
            )
            log.critical(msg=not_in_storage_error, extra={"file_id": file_id})
            raise not_in_storage_error

        # Copy the file from permanent storage bucket to the outbox (download) bucket
        try:
            await object_storage.copy_object(
                source_bucket_id=permanent_bucket_id,
                source_object_id=file.object_id,
                dest_bucket_id=outbox_bucket_id,
                dest_object_id=outbox_object_id,
            )
        except object_storage.ObjectAlreadyExistsError:
            # the content is already where it should go, there is nothing to do
            log.info(
                "Object corresponding to file ID '%s' is already in the outbox.",
                file_id,
            )
            return
        except Exception as exc:
            # Irreconcilable object error -- event needs investigation
            obj_error = self.CopyOperationError(
                file_id=file_id, dest_bucket_id=outbox_bucket_id, exc_text=str(exc)
            )
            log.critical(obj_error)
            raise obj_error from exc

        log.info(
            "Object corresponding to file ID '%s' has been staged to the outbox.",
            file_id,
        )

        await self._event_publisher.file_staged_for_download(
            file_id=file_id,
            decrypted_sha256=decrypted_sha256,
            target_object_id=outbox_object_id,
            target_bucket_id=outbox_bucket_id,
            storage_alias=file.storage_alias,
        )

    async def delete_file(self, *, file_id: str) -> None:
        """Deletes a file from the permanent storage and the internal database.
        If no file with that id exists, do nothing.

        Args:
            file_id:
                id for the file to delete.
        """
        try:
            file = await self._file_metadata_dao.get_by_id(file_id)
        except ResourceNotFoundError:
            # resource not in database, nothing to do
            log.info(
                "File with ID '%s' was not found in the database. Deletion cancelled.",
                file_id,
            )
            return

        # Get object ID and storage instance
        object_id = file.object_id
        bucket_id, object_storage = self._object_storages.for_alias(file.storage_alias)

        # Try to remove file from S3
        with suppress(object_storage.ObjectNotFoundError):
            # If file does not exist anyways, we are done.
            await object_storage.delete_object(bucket_id=bucket_id, object_id=object_id)

        # Try to remove file from database
        with suppress(ResourceNotFoundError):
            # If file does not exist anyways, we are done.
            await self._file_metadata_dao.delete(id_=file_id)

        log.info(
            "Finished object storage and metadata deletion for file ID '%s'", file_id
        )
        await self._event_publisher.file_deleted(file_id=file_id)
