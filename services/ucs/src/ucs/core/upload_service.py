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

import logging
import uuid
from collections.abc import Callable
from contextlib import suppress

from ghga_service_commons.utils.multinode_storage import ObjectStorages
from hexkit.utils import calc_part_size, now_utc_ms_prec

from ucs.core import models
from ucs.ports.inbound.upload_service import UploadServicePort
from ucs.ports.outbound.dao import (
    DaoCollectionPort,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
)
from ucs.ports.outbound.event_pub import EventPublisherPort

log = logging.getLogger(__name__)


class UploadService(UploadServicePort):
    """Service for handling multi-part uploads to the Inbox storage."""

    def __init__(
        self,
        *,
        daos: DaoCollectionPort,
        object_storages: ObjectStorages,
        event_publisher: EventPublisherPort,
        # domain internal dependencies are immediately injected:
        part_size_calculator: Callable[[int], int] = lambda file_size: calc_part_size(
            file_size=file_size
        ),
    ):
        """Initialize class instance with configs and outbound adapter objects."""
        self._daos = daos
        self._object_storages = object_storages
        self._event_publisher = event_publisher
        self._part_size_calculator = part_size_calculator

    async def _get_upload_if_status(
        self, upload_id: str, status: models.UploadStatus
    ) -> models.UploadAttempt:
        """Makes sure that the upload with the given ID exists and that its current
        status matches the specified status. If that is the case, the upload is returned.
        Otherwise an UploadStatusMismatchError is raised.
        """
        upload = await self.get_details(upload_id=upload_id)

        if upload.status != status:
            status_mismatch_error = self.UploadStatusMismatchError(
                upload_id=upload.upload_id,
                expected_status=status,
                current_status=upload.status,
            )
            log.error(
                status_mismatch_error,
                extra={
                    "upload_id": upload.upload_id,
                    "expected_status": status,
                    "current_status": upload.status,
                },
            )
            raise status_mismatch_error

        return upload

    async def _cancel_with_final_status(
        self, *, upload_id: str, final_status: models.UploadStatus
    ) -> None:
        """
        Cancel the multi-part upload with the given ID and set the specified final
        status.
        """
        upload = await self._get_upload_if_status(
            upload_id, status=models.UploadStatus.PENDING
        )

        bucket_id, object_storage = self._object_storages.for_alias(
            upload.storage_alias
        )

        # mark the upload as aborted in the object storage:
        try:
            await object_storage.abort_multipart_upload(
                upload_id=upload_id,
                bucket_id=bucket_id,
                object_id=upload.object_id,
            )
        except object_storage.MultiPartUploadAbortError as error:
            multipart_cancel_error = self.UploadCancelError(upload_id=upload_id)
            log.error(multipart_cancel_error, extra={"upload_id": upload_id})
            raise multipart_cancel_error from error
        except object_storage.MultiPartUploadNotFoundError:
            # This correspond to an inconsistency between the database and
            # the storage, however, since this cancel method might be used to
            # resolve this inconsistency, this exception will be ignored.
            pass

        # change the final status of the upload in the database:
        updated_upload = upload.model_copy(update={"status": final_status})
        await self._daos.upload_attempts.update(updated_upload)

        log.warning(
            "Aborted multipart upload with id '%s' and set attempt status to '%s'.",
            upload_id,
            final_status,
        )

    async def _clear_latest_with_final_status(
        self, *, file_id: str, final_status: models.UploadStatus
    ):
        """Clear a multi-part upload after receiving a final accept/reject decision."""
        try:
            file = await self._daos.file_metadata.get_by_id(file_id)
        except ResourceNotFoundError as error:
            # File ID is immutable across services, so if we get an invalid file ID
            # from a downstream service event, something is seriously wrong
            unknown_file_id = self.FileUnknownError(file_id=file_id)
            log.critical(unknown_file_id, extra={"file_id": file_id})
            raise unknown_file_id from error

        if file.latest_upload_id is None:
            no_upload = self.NoLatestUploadError(file_id=file_id)
            log.error(no_upload, extra={"file_id": file_id})
            raise no_upload

        latest_upload = await self.get_details(upload_id=file.latest_upload_id)
        current_status = latest_upload.status

        if latest_upload.status != models.UploadStatus.UPLOADED:
            status_mismatch_error = self.UploadStatusMismatchError(
                upload_id=latest_upload.upload_id,
                expected_status=models.UploadStatus.UPLOADED,
                current_status=current_status,
            )
            log.error(
                status_mismatch_error,
                extra={
                    "upload_id": latest_upload.upload_id,
                    "expected_status": models.UploadStatus.UPLOADED,
                    "current_status": current_status,
                },
            )
            if current_status in (
                models.UploadStatus.ACCEPTED,
                models.UploadStatus.FAILED,
                models.UploadStatus.REJECTED,
            ):
                # This state can be reached when consuming an event that has already
                # been seen, i.e. this does not necessarily represent an inconsistency
                # so simply abort processing here
                return

            if current_status != models.UploadStatus.UPLOADED:
                # Seeing any other status probably means there is some inconsistency
                # across services, so it should be ok to crash so nothing else is
                # processed in the meantime
                raise status_mismatch_error

        # remove the object from object storage:
        bucket_id, object_storage = self._object_storages.for_alias(
            latest_upload.storage_alias
        )
        try:
            await object_storage.delete_object(
                bucket_id=bucket_id,
                object_id=latest_upload.object_id,
            )
        except object_storage.ObjectNotFoundError as error:
            # This means the database and object storage are out of sync
            # In this case, set the upload status to failed as there's nothing else this
            # service can do about the situation
            final_status = models.UploadStatus.FAILED

            db_storage_not_synchronized = self.StorageAndDatabaseOutOfSyncError(
                problem=(
                    f"Trying to clear the upload with ID {latest_upload.upload_id}"
                    + f" for file with file ID {file_id} (final status: {final_status}),"
                    + " however, the corresponding file with object ID"
                    + f" {latest_upload.object_id} could not be found in object storage."
                )
            )
            log.critical(
                db_storage_not_synchronized,
                extra={
                    "upload_id": latest_upload.upload_id,
                    "file_id": file_id,
                    "object_id": latest_upload.object_id,
                },
            )
            raise db_storage_not_synchronized from error
        finally:
            # mark the upload as either accepted, rejected or failed in the database:
            updated_upload = latest_upload.model_copy(update={"status": final_status})
            await self._daos.upload_attempts.update(updated_upload)

        log.info(
            "Successfully set upload status for file '%s' to '%s'.",
            file_id,
            final_status,
        )

    async def _assert_no_active_upload(self, *, file_id: str) -> None:
        """Asserts that there is no upload currently active for the file with the given
        ID. Otherwise, raises an ExistingActiveUploadError.
        """
        existing_attempts = self._daos.upload_attempts.find_all(
            mapping={"file_id": file_id}
        )
        async for attempt in existing_attempts:
            if attempt.status in (
                models.UploadStatus.ACCEPTED,
                models.UploadStatus.PENDING,
                models.UploadStatus.UPLOADED,
            ):
                active_upload_exists = self.ExistingActiveUploadError(
                    active_upload=attempt
                )
                log.error(active_upload_exists)
                raise active_upload_exists

    async def _init_multipart_upload(
        self, *, file_id: str, object_id: str, storage_alias: str
    ) -> str:
        """Initialize a new multipart upload and returns the upload ID.
        This will only interact with the object storage but not update the database.
        """
        try:
            bucket_id, object_storage = self._object_storages.for_alias(storage_alias)
        except KeyError as error:
            unknown_alias = self.UnknownStorageAliasError(storage_alias=storage_alias)
            log.error(unknown_alias, extra={"storage_alias": storage_alias})
            raise unknown_alias from error
        try:
            return await object_storage.init_multipart_upload(
                bucket_id=bucket_id, object_id=object_id
            )
        except object_storage.MultiPartUploadAlreadyExistsError as error:
            # FIXME in multinode PR? This only means there is an ongoing multipart upload,
            # the complete file is not in the inbox yet, so the error is misleading
            file_in_inbox = self.FileAlreadyInInboxError(file_id=file_id)
            log.error(file_in_inbox, extra={"file_id": file_id})
            raise file_in_inbox from error

    async def _insert_upload(self, *, upload: models.UploadAttempt) -> None:
        """Insert a new upload attempt to the database assuming a corresponding
        multipart upload has already been initiated at the object storage.
        If that operation fails unexpectedly, the initiation of the upload at
        the object storage is rolled back.
        """
        try:
            await self._daos.upload_attempts.insert(upload)
        except ResourceAlreadyExistsError as error:
            # One source of error might be that an upload with the given ID
            # already exists. In that case the assumption that the object
            # storage assigns unique IDs is violated. However, at this stage
            # there is nothing we can do to handel this exception.
            bucket_id, object_storage = self._object_storages.for_alias(
                upload.storage_alias
            )
            await object_storage.abort_multipart_upload(
                upload_id=upload.upload_id,
                bucket_id=bucket_id,
                object_id=upload.object_id,
            )
            log.error(
                error,
                extra={
                    "upload_id": upload.upload_id,
                    "bucket_id": bucket_id,
                    "object_id": upload.object_id,
                },
            )
            raise

    async def _set_latest_upload_for_file(
        self, *, file: models.FileMetadata, new_upload_id: str, object_id: str
    ) -> None:
        """Sets the `latest_upload_id` metadata field of the specified file in the
        database to the provided new_upload_id.
        It is assumed that a multipart upload has already been initiated at the object
        storage and that a new upload entry was persisted to the database.
        If this operation fails unexpectedly, both the database and the object storage
        are roled back by eliminating any traces of this new upload.
        """
        updated_file = file.model_copy(update={"latest_upload_id": new_upload_id})
        try:
            await self._daos.file_metadata.update(updated_file)
        except ResourceNotFoundError as error:
            latest_upload_attempt = await self._daos.upload_attempts.get_by_id(
                id_=new_upload_id
            )
            bucket_id, object_storage = self._object_storages.for_alias(
                latest_upload_attempt.storage_alias
            )
            # this shouldn't happen, but if it does, we need to cleanup:
            await object_storage.abort_multipart_upload(
                upload_id=new_upload_id,
                bucket_id=bucket_id,
                object_id=object_id,
            )
            await self._daos.upload_attempts.delete(id_=new_upload_id)
            log.error(
                error,
                extra={
                    "upload_id": new_upload_id,
                    "bucket_id": bucket_id,
                    "object_id": object_id,
                },
            )
            raise

    async def initiate_new(
        self, *, file_id: str, submitter_public_key: str, storage_alias: str
    ) -> models.UploadAttempt:
        """Initiates a new multi-part upload for the file with the given ID."""
        try:
            file = await self._daos.file_metadata.get_by_id(file_id)
        except ResourceNotFoundError as error:
            raise self.FileUnknownError(file_id=file_id) from error

        await self._assert_no_active_upload(file_id=file_id)

        # Generate the new object ID for the file
        object_id = str(uuid.uuid4())
        log.debug(
            "Generated new object ID '%s' for file with ID '%s'.", object_id, file_id
        )

        upload_id = await self._init_multipart_upload(
            file_id=file_id, object_id=object_id, storage_alias=storage_alias
        )
        log.info("Started multipart upload for file '%s'.", file_id)

        # get the recommended part size:
        part_size = self._part_size_calculator(file.decrypted_size)
        log.debug("Calculated part size for upload: %i", part_size)

        # assemble the upload attempts details:
        upload = models.UploadAttempt(
            upload_id=upload_id,
            file_id=file_id,
            object_id=object_id,
            status=models.UploadStatus.PENDING,
            part_size=part_size,
            creation_date=now_utc_ms_prec(),
            completion_date=None,
            submitter_public_key=submitter_public_key,
            storage_alias=storage_alias,
        )

        await self._insert_upload(upload=upload)
        await self._set_latest_upload_for_file(
            file=file, new_upload_id=upload_id, object_id=object_id
        )
        log.info(
            "Created database entry for upload attempt '%s' of file '%s'.",
            upload_id,
            file_id,
        )

        return upload

    async def get_details(self, *, upload_id: str) -> models.UploadAttempt:
        """Get details on an existing multipart upload by specifing its ID."""
        try:
            return await self._daos.upload_attempts.get_by_id(upload_id)
        except ResourceNotFoundError as error:
            unknown_upload = self.UnknownUploadError(upload_id=upload_id)
            log.error(unknown_upload, extra={"upload_id": upload_id})
            raise unknown_upload from error

    async def create_part_url(self, *, upload_id: str, part_no: int) -> str:
        """
        Create and return a pre-signed URL to upload the bytes for the file part with
        the given number of the upload with the given ID.
        """
        upload = await self._get_upload_if_status(
            upload_id, status=models.UploadStatus.PENDING
        )

        bucket_id, object_storage = self._object_storages.for_alias(
            upload.storage_alias
        )
        try:
            return await object_storage.get_part_upload_url(
                upload_id=upload_id,
                bucket_id=bucket_id,
                object_id=upload.object_id,
                part_number=part_no,
            )
        except object_storage.MultiPartUploadNotFoundError as error:
            db_storage_not_synchronized = self.StorageAndDatabaseOutOfSyncError(
                problem=(
                    f"The upload attempt with ID {upload_id} was marked as 'pending' in"
                    + "the database, but no corresponding upload exists in the object"
                    + "storage."
                )
            )
            log.error(
                db_storage_not_synchronized,
                extra={
                    "upload_id": upload_id,
                    "bucket_id": bucket_id,
                    "object_id": upload.object_id,
                },
            )
            raise db_storage_not_synchronized from error

    async def complete(self, *, upload_id: str) -> None:
        """Confirm the completion of the multi-part upload with the given ID."""
        upload = await self._get_upload_if_status(
            upload_id, status=models.UploadStatus.PENDING
        )

        # mark the upload as complete in the object storage:
        bucket_id, object_storage = self._object_storages.for_alias(
            upload.storage_alias
        )
        try:
            await object_storage.complete_multipart_upload(
                upload_id=upload_id,
                bucket_id=bucket_id,
                object_id=upload.object_id,
            )
        except object_storage.MultiPartUploadConfirmError as error:
            # This can typically not be repaired, so aborting the upload attempt
            # and marking it as failed in the database:
            await self._cancel_with_final_status(
                upload_id=upload_id, final_status=models.UploadStatus.FAILED
            )
            upload_completion_error = self.UploadCompletionError(
                upload_id=upload_id, reason=str(error)
            )
            log.error(upload_completion_error, extra={"upload_id": upload_id})
            raise upload_completion_error from error

        # mark the upload as complete (uploaded) in the database:
        completion_date = now_utc_ms_prec()
        updated_upload = upload.model_copy(
            update={
                "status": models.UploadStatus.UPLOADED,
                "completion_date": completion_date,
            }
        )
        await self._daos.upload_attempts.update(updated_upload)
        log.info("Marked upload '%s' as completed.", upload_id)

        # publish an event relaying that a new upload was received:
        file = await self._daos.file_metadata.get_by_id(upload.file_id)
        await self._event_publisher.publish_upload_received(
            file_metadata=file,
            upload_date=completion_date,
            submitter_public_key=updated_upload.submitter_public_key,
            object_id=upload.object_id,
            bucket_id=bucket_id,
            storage_alias=upload.storage_alias,
        )
        log.debug("Sent upload received event for upload '%s'", upload_id)

    async def cancel(self, *, upload_id: str) -> None:
        """Cancel the multi-part upload with the given ID."""
        await self._cancel_with_final_status(
            upload_id=upload_id, final_status=models.UploadStatus.CANCELLED
        )

    async def accept_latest(self, *, file_id: str) -> None:
        """
        Accept the latest multi-part upload for the given file.

        Here the file ID is used, as this method is triggered by downstream services
        that only know the file ID not the upload attempt.
        """
        await self._clear_latest_with_final_status(
            file_id=file_id, final_status=models.UploadStatus.ACCEPTED
        )

    async def reject_latest(self, *, file_id: str) -> None:
        """
        Reject the latest multi-part upload for the given file.

        Here the file ID is used, as this method is triggered by downstream services
        that only know the file ID not the upload attempt.
        """
        await self._clear_latest_with_final_status(
            file_id=file_id, final_status=models.UploadStatus.REJECTED
        )

    async def deletion_requested(self, *, file_id: str) -> None:
        """
        Cancel the current upload attempt for the given file and remove all associated
        data related to upload attempts and file metadata.
        An event will be published if the deletion is successful, but only in the case
        that something exists to delete.
        """
        with suppress(ResourceNotFoundError):
            await self._daos.file_metadata.delete(id_=file_id)

        attempts_found = False

        # delete upload attempt metadata and associated objects, if present
        async for attempt in self._daos.upload_attempts.find_all(
            mapping={"file_id": file_id}
        ):
            attempts_found = True
            try:
                storage_alias = attempt.storage_alias
                bucket_id, object_storage = self._object_storages.for_alias(
                    endpoint_alias=storage_alias
                )
            except KeyError as error:
                unknown_storage_alias = self.UnknownStorageAliasError(
                    storage_alias=storage_alias
                )
                log.critical(
                    unknown_storage_alias, extra={"storage_alias": storage_alias}
                )
                raise unknown_storage_alias from error

            # could probably be simplified to only delete for the latest Upload ID
            # but as we currently are not sure if all things are deleted correctly
            # when they should be, let's be thorough for now
            if await object_storage.does_object_exist(
                bucket_id=bucket_id, object_id=attempt.object_id
            ):
                await object_storage.delete_object(
                    bucket_id=bucket_id, object_id=attempt.object_id
                )
            # no way to check, just run and ignore exception
            with suppress(object_storage.MultiPartUploadNotFoundError):
                await object_storage.abort_multipart_upload(
                    bucket_id=bucket_id,
                    object_id=attempt.object_id,
                    upload_id=attempt.upload_id,
                )
            await self._daos.upload_attempts.delete(id_=attempt.upload_id)

        if attempts_found:
            await self._event_publisher.publish_deletion_successful(file_id=file_id)
