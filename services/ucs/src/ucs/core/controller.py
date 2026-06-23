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

"""Implements the UploadController class to manage file uploads"""

import contextlib
import logging
from datetime import timedelta
from math import ceil
from typing import Any
from uuid import uuid4

from ghga_event_schemas.pydantic_ import (
    FileInternallyRegistered,
    InterrogationFailure,
    InterrogationSuccess,
)
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.protocols.dao import (
    DaoError,
    MultipleHitsFoundError,
    NoHitsFoundError,
    UniqueConstraintViolationError,
)
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from ucs.config import Config
from ucs.constants import MAX_PART_COUNT, MAX_PART_SIZE, MIN_PART_SIZE
from ucs.core.models import (
    FileUpload,
    FileUploadBasics,
    FileUploadBox,
    UploadActivity,
)
from ucs.ports.inbound.controller import UploadControllerPort
from ucs.ports.outbound.dao import (
    FileUploadBoxDao,
    FileUploadDao,
    ResourceNotFoundError,
    UploadActivityDao,
)
from ucs.ports.outbound.storage import S3ClientPort

log = logging.getLogger(__name__)


class UploadController(UploadControllerPort):
    """A class for managing file uploads"""

    def __init__(
        self,
        *,
        config: Config,
        file_upload_box_dao: FileUploadBoxDao,
        file_upload_dao: FileUploadDao,
        upload_activity_dao: UploadActivityDao,
        s3_client: S3ClientPort,
    ):
        self._config = config
        self._file_upload_box_dao = file_upload_box_dao
        self._file_upload_dao = file_upload_dao
        self._upload_activity_dao = upload_activity_dao
        self._s3_client = s3_client

    async def _get_box_at_version(
        self, *, box_id: UUID4, version: int
    ) -> FileUploadBox:
        """Fetch a FileUploadBox and verify the version matches.

        Raises:
        - `BoxNotFoundError` if the box is not in the DB.
        - `BoxVersionError` if the version doesn't match.
        """
        try:
            box = await self._file_upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.BoxNotFoundError(box_id=box_id)
            log.error(error)
            raise error from err

        if box.version != version:
            error = self.BoxVersionError(box_id=box_id)
            log.error(error, extra={"box_id": box_id, "version": version})
            raise error

        return box

    async def _insert_file_upload(
        self,
        *,
        box: FileUploadBox,
        file_upload: FileUpload,
    ) -> None:
        """Insert a new FileUpload, replacing a failed/cancelled one if needed.

        If a unique constraint violation occurs, the existing upload is retrieved and
        replaced when it is in a failed or cancelled state. If any other error occurs,
        the upload is marked 'failed' so a subsequent retry can replace it, and the
        error is re-raised. The associated S3 multipart upload is left for the cleanup
        job to handle.

        Raises `FileUploadAlreadyExists` if an active FileUpload already exists for
        this alias and box_id (and is not failed or cancelled).
        """
        box_id = box.id
        alias = file_upload.alias

        try:
            await self._file_upload_dao.insert(file_upload)
        except UniqueConstraintViolationError as err:
            # If there's already a FileUpload in the box with this alias, retrieve it
            logging_extras = {  # only for logging
                "box_id": box.id,
                "file_alias": file_upload.alias,
                "new_file_upload_id": file_upload.id,
            }
            try:
                existing_upload = await self._file_upload_dao.find_one(
                    mapping={"box_id": box_id, "alias": alias}
                )
            except (NoHitsFoundError, MultipleHitsFoundError) as find_err:
                # If we don't get any hits, something weird is going on. This isn't a
                #  typical error to handle, so raise a RuntimeError
                qty = "no" if isinstance(find_err, NoHitsFoundError) else "multiple"
                msg = (
                    "Encountered an error indicating this FileUploadBox already"
                    + f" has a FileUpload for the alias {alias}, but got {qty} results"
                    + " when trying to retrieve the existing FileUpload."
                )
                log.error(msg)
                raise RuntimeError(msg) from err
            except Exception as other_err:
                # If another error occurs during find_one, log it too
                msg = (
                    "Encountered an error indicating this FileUploadBox already"
                    + f" has a FileUpload for the alias {alias}, but received the"
                    + f" following error while trying to investigate: {other_err}"
                )
                log.error(msg, extra=logging_extras)
                raise RuntimeError(msg) from other_err

            # If retrieval succeeds, evaluate and attempt to replace the file upload
            logging_extras["old_file_upload_id"] = existing_upload.id
            logging_extras["old_state"] = existing_upload.state
            replaced = await self._try_to_replace_upload(
                existing_upload=existing_upload,
                new_upload=file_upload,
                logging_extras=logging_extras,
            )

            # This means that the existing file is still "good" and needs explicit
            #  cancellation/removal before a new upload can be started for this alias.
            if not replaced:
                error = self.FileUploadAlreadyExists(alias=alias)
                log.error(error, extra=logging_extras)
                raise error from None  # don't need Unique* error in the trace
        except Exception as err:
            # This branch handles all other errors that *don't* signify an existing file
            # If, e.g. kafka raises an error, delete the FileUpload so user can retry.
            # To avoid more potential failure points, let active S3 upload linger until
            #  the cleanup job takes care of it.
            extra = {"box_id": file_upload.box_id, "file_alias": file_upload.alias}
            log.error(
                "Encountered an error while inserting FileUpload %s; it will be marked"
                + " as 'failed'. Error: %s",
                file_upload.id,
                err,
                extra=extra,
            )

            file_upload.state = "failed"
            file_upload.state_updated = now_utc_ms_prec()
            file_upload.failure_reason = "Internal error during upload initiation"
            # If Kafka is the problem, this will also error but not until after the update
            try:
                # In case first write didn't actually land, use upsert
                await self._file_upload_dao.upsert(file_upload)
            except Exception as mark_failed_err:
                # TODO: Update this section once Hexkit has defined errors for Kafka
                if isinstance(mark_failed_err, DaoError):
                    # Database errors should be raised, not suppressed
                    log.error(
                        "While marking FileUpload %s as 'failed', encountered another"
                        + " database error: %s",
                        file_upload.id,
                        mark_failed_err,
                        extra=extra,
                    )
                    raise mark_failed_err
                else:
                    log.warning(
                        "While marking FileUpload %s as 'failed', encountered another error."
                        + " If it's from Kafka, this is fine - just fix Kafka and run"
                        + " the publish-all job. If it's not related to Kafka at all,"
                        + " then this warrants further investigation. Error: %s",
                        file_upload.id,
                        mark_failed_err,
                    )

            # This is INFO level because it's normal procedure for cleanup.
            log.info(
                "Marked FileUpload %s as 'failed' due to error during initiation.",
                file_upload.id,
                extra=extra,
            )
            # Re-raise the exception
            raise

    async def _try_to_replace_upload(
        self,
        existing_upload: FileUpload,
        new_upload: FileUpload,
        logging_extras: dict[str, Any],
    ) -> bool:
        """Try to replace an existing FileUpload for a given box and alias.

        If successful, this method will delete the old FileUpload and insert the new one.
        This does result in an outbox deletion event for the old FileUpload.

        The old FileUpload is deleted, rather than re-used, to avoid complications with
        downstream state management. Also, we can't have two FileUpload docs with the
        same box ID and alias because it will violate the index.

        Returns a boolean indicating whether replacement was successful.
        """
        # Examine the existing FileUpload - it has to be either failed or cancelled to
        #  be replaced with the new submission. If not, we have to raise an error.
        #  The user (or a DS) must first stop/remove the upload before it can be
        #  replaced with a new one.
        if existing_upload.state not in ("failed", "cancelled"):
            return False

        log.info(
            "Replacing %s FileUpload %s for alias '%s' with new upload %s",
            existing_upload.state,
            existing_upload.id,
            new_upload.alias,
            new_upload.id,
            extra=logging_extras,
        )
        await self._file_upload_dao.delete(existing_upload.id)
        await self._file_upload_dao.insert(new_upload)
        return True

    async def _get_unlocked_box(self, *, box_id: UUID4) -> FileUploadBox:
        """Retrieve a FileUploadBox by ID.

        Raises:
        - `BoxNotFoundError` if the box does not exist
        - `BoxStateError` if the box exists but is locked or archived.
        """
        # Verify that the box exists
        try:
            box = await self._file_upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.BoxNotFoundError(box_id=box_id)
            log.error(error)
            raise error from err

        # Verify that the box is not locked or archived
        if box.state != "open":
            error = self.BoxStateError(box_id=box_id, box_state=box.state)
            log.error(error)
            raise error

        return box

    async def _remove_completed_file_upload(self, *, file_upload: FileUpload) -> None:
        """Delete a completely uploaded file from S3 or abort any stale multipart.

        Does not delete any data from the DB.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
          If this occurs, developer intervention might be required.
        - `BucketMissingError` if the configured bucket does not exist in S3.
        - `S3OperationError` if S3 returns any other unexpected error.
        """
        try:
            await self._s3_client.delete_inbox_file(file_upload=file_upload)
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=file_upload.storage_alias
            ) from err
        except S3ClientPort.S3UploadAbortError as err:
            raise self.UploadAbortError(
                file_id=file_upload.id,
                s3_upload_id=file_upload.s3_upload_id,
                bucket_id=file_upload.bucket_id,
            ) from err
        except S3ClientPort.BucketNotFoundError as err:
            raise self.BucketMissingError(bucket_id=file_upload.bucket_id) from err
        except S3ClientPort.S3OperationError as err:
            raise self.S3OperationError(details=str(err)) from err

    async def _remove_incomplete_file_upload(self, *, file_upload: FileUpload) -> None:
        """Abort an incomplete S3 multipart upload.

        Does not delete any data from the DB.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        - `BucketMissingError` if the configured bucket does not exist in S3.
        - `S3OperationError` if S3 returns any other unexpected error.
        """
        try:
            await self._s3_client.abort_multipart_upload(
                storage_alias=file_upload.storage_alias,
                object_id=str(file_upload.object_id),
                s3_upload_id=file_upload.s3_upload_id,
                file_id=file_upload.id,
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=file_upload.storage_alias
            ) from err
        except S3ClientPort.S3UploadAbortError as err:
            raise self.UploadAbortError(
                file_id=file_upload.id,
                s3_upload_id=file_upload.s3_upload_id,
                bucket_id=file_upload.bucket_id,
            ) from err
        except S3ClientPort.BucketNotFoundError as err:
            raise self.BucketMissingError(bucket_id=file_upload.bucket_id) from err
        except S3ClientPort.S3OperationError as err:
            raise self.S3OperationError(details=str(err)) from err

    async def initiate_file_upload(
        self,
        *,
        box_id: UUID4,
        alias: str,
        decrypted_size: int,
        encrypted_size: int,
        part_size: int,
    ) -> tuple[UUID4, str]:
        """Initialize a new multipart upload.

        Returns the file ID and storage alias as a 2-tuple.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `BoxStateError` if the box exists but is locked.
        - `BoxMaxSizeExceededError` if adding the file would exceed the box's size limit.
        - `TooManyOpenUploadsError` if the box is already at the concurrent upload limit.
        - `FileUploadAlreadyExists` if there's already a FileUpload for this alias.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAlreadyInProgressError` if an upload is already in progress.
        - `PartSizeError` if the specified part size would results in more
            parts than S3 allows, or is smaller or larger than what S3 allows.
        """
        extra: dict[str, Any] = {"box_id": box_id, "alias": alias}
        # Get the box and resolve S3 storage details
        box = await self._get_unlocked_box(box_id=box_id)
        storage_alias = box.storage_alias
        try:
            bucket_id = self._s3_client.get_bucket_id_for_alias(
                storage_alias=storage_alias
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(storage_alias=storage_alias) from err
        extra["storage_alias"] = storage_alias
        extra["bucket_id"] = bucket_id

        # Get both box size + in progress size and the number of in progress files
        current_size = box.size
        in_progress_count = 0
        async for upload in self._file_upload_dao.find_all(
            mapping={"box_id": box.id, "state": "init"}
        ):
            current_size += upload.decrypted_size
            in_progress_count += 1

        # Ensure that another upload is allowed at the moment
        max_concurrent = self._config.max_concurrent_uploads_per_box
        if in_progress_count >= max_concurrent:
            error = self.TooManyOpenUploadsError(
                box_id=box.id, max_concurrent=max_concurrent
            )
            log.error(error, extra=extra)
            raise error

        # Ensure file size doesn't exceed box limit
        if current_size + decrypted_size > box.max_size:
            error = self.BoxMaxSizeExceededError(
                box_id=box.id, max_size=box.max_size, current_size=current_size
            )
            log.error(error, extra=extra)
            raise error

        # Ensure part size is okay - verify size & implied part count. Min and Max part
        #  size are enforced by the pydantic model at ingress, but double-checked here
        if (
            not (MIN_PART_SIZE <= part_size <= MAX_PART_SIZE)
            or ceil(encrypted_size / part_size) > MAX_PART_COUNT
        ):
            raise self.PartSizeError(file_alias=alias, part_size=part_size)

        file_id = uuid4()
        object_id = uuid4()
        initiated = now_utc_ms_prec()

        file_upload_basics = FileUploadBasics(
            id=file_id,
            box_id=box.id,
            alias=alias,
            storage_alias=storage_alias,
            bucket_id=bucket_id,
            object_id=object_id,
            decrypted_size=decrypted_size,
            encrypted_size=encrypted_size,
            part_size=part_size,
        )

        # Initiate a new multipart file upload on S3
        try:
            s3_upload_id = await self._s3_client.init_multipart_upload(
                file_upload_basics=file_upload_basics
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(storage_alias=storage_alias) from err
        except S3ClientPort.OrphanedMultipartUploadError as err:
            #  Each upload uses a freshly generated object_id, so a collision is
            #  extremely unlikely. The most likely cause is a crash between a previous
            #  S3 init and the subsequent DB insert. We can't assign S3 upload IDs, so
            #  that data isn't recoverable programmatically — manual intervention is
            #  needed to cancel the orphaned upload.
            log.critical(str(err), extra=extra)
            raise self.UploadAlreadyInProgressError(
                file_id=file_id, bucket_id=bucket_id
            ) from err
        except S3ClientPort.BucketNotFoundError as err:
            raise self.BucketMissingError(bucket_id=bucket_id) from err
        except S3ClientPort.S3OperationError as err:
            raise self.S3OperationError(details=str(err)) from err

        # Build and insert the complete FileUpload record
        file_upload = FileUpload(
            id=file_id,
            box_id=box.id,
            alias=alias,
            state="init",
            state_updated=now_utc_ms_prec(),
            storage_alias=storage_alias,
            bucket_id=bucket_id,
            object_id=object_id,
            decrypted_size=decrypted_size,
            encrypted_size=encrypted_size,
            part_size=part_size,
            s3_upload_id=s3_upload_id,
            initiated=initiated,
        )

        # Extensive recovery/error handling occurs here:
        await self._insert_file_upload(box=box, file_upload=file_upload)

        # Create upload activity entry (overwrite if one unexpectedly exists)
        await self._upload_activity_dao.upsert(
            UploadActivity(file_id=file_id, last_activity=now_utc_ms_prec())
        )

        log.info(
            "FileUpload %s created for alias %s with S3 multipart upload ID %s.",
            file_id,
            alias,
            s3_upload_id,
            extra=extra,
        )
        return file_id, storage_alias

    async def get_part_upload_url(self, *, file_id: UUID4, part_no: int) -> str:
        """
        Create and return a pre-signed URL to upload the bytes for the file part with
        the given number of the upload with the given file ID.

        Raises:
        - `FileUploadNotFound` if the FileUpload is not found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadSessionNotFoundError` if the upload session can't be found.
        """
        try:
            file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.FileUploadNotFound(file_id=file_id)
            log.error(
                error,
                extra={"file_id": file_id, "part_no": part_no},
            )
            raise error from err

        s3_upload_id = file_upload.s3_upload_id
        try:
            return await self._s3_client.get_part_upload_url(
                file_upload=file_upload, part_no=part_no
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=file_upload.storage_alias
            ) from err
        except S3ClientPort.S3UploadNotFoundError as err:
            log.error(
                err,
                extra={
                    "s3_upload_id": s3_upload_id,
                    "file_id": file_id,
                    "bucket_id": file_upload.bucket_id,
                    "part_no": part_no,
                    "storage_alias": file_upload.storage_alias,
                },
            )
            raise self.UploadSessionNotFoundError(
                bucket_id=file_upload.bucket_id, s3_upload_id=s3_upload_id
            ) from err
        except S3ClientPort.BucketNotFoundError as err:
            raise self.BucketMissingError(bucket_id=file_upload.bucket_id) from err
        except S3ClientPort.S3OperationError as err:
            raise self.S3OperationError(details=str(err)) from err

    async def refresh_upload_activity(self, *, file_id: UUID4) -> None:
        """Update the activity timestamp for an in-progress upload.

        Exceptions are caught and logged so uploads aren't interrupted for something
        that is only needed for cleanup.
        """
        try:
            await self._upload_activity_dao.upsert(
                UploadActivity(file_id=file_id, last_activity=now_utc_ms_prec())
            )
        except Exception:
            log.exception(
                "Failed to refresh activity entry for file %s.", file_id, exc_info=True
            )

    async def _compare_checksums(
        self,
        file_upload: FileUpload,
        expected_checksum: str,
    ) -> None:
        """Verify that the S3-calculated object ETag (MD5) matches the submitted MD5
        checksum of the encrypted file content. This is effectively an integrity check
        for the file upload itself.

        If the checksums don't match, this function marks the FileUpload as failed and
        raises a ChecksumMismatchError.
        """
        file_id = file_upload.id
        object_id = file_upload.object_id
        try:
            actual_checksum = await self._s3_client.get_object_etag(
                file_upload=file_upload, object_id=object_id
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=file_upload.storage_alias
            ) from err
        except S3ClientPort.BucketNotFoundError as err:
            raise self.BucketMissingError(bucket_id=file_upload.bucket_id) from err
        except S3ClientPort.S3ObjectNotFoundError as err:
            raise self.S3ObjectMissingError(
                bucket_id=file_upload.bucket_id, object_id=str(object_id)
            ) from err
        except S3ClientPort.S3OperationError as err:
            raise self.S3OperationError(details=str(err)) from err

        if actual_checksum != expected_checksum:
            # Mark upload as failed, then raise an error
            file_upload.state = "failed"
            file_upload.state_updated = now_utc_ms_prec()
            file_upload.failure_reason = "Upload integrity checksum mismatch"
            await self._file_upload_dao.update(file_upload)
            log.info("Marked FileUpload %s as 'failed'.", file_id)
            error = self.ChecksumMismatchError(file_id=file_id)
            extra = {
                "bucket_id": file_upload.bucket_id,
                "file_id": file_id,
                "object_id": object_id,
                "expected_checksum": expected_checksum,
                "actual_checksum": actual_checksum,
            }
            log.error(error, extra=extra)
            raise error

    async def _verify_object_size(self, *, file_upload: FileUpload) -> None:
        """Verify that the S3 object size matches the declared encrypted_size.

        If the sizes don't match, marks the FileUpload as failed and raises
        UploadSizeMismatchError.
        """
        file_id = file_upload.id
        object_id = file_upload.object_id
        try:
            actual_size = await self._s3_client.get_object_size(
                file_upload=file_upload, object_id=object_id
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=file_upload.storage_alias
            ) from err
        except S3ClientPort.BucketNotFoundError as err:
            raise self.BucketMissingError(bucket_id=file_upload.bucket_id) from err
        except S3ClientPort.S3ObjectNotFoundError as err:
            raise self.S3ObjectMissingError(
                bucket_id=file_upload.bucket_id, object_id=str(object_id)
            ) from err
        except S3ClientPort.S3OperationError as err:
            raise self.S3OperationError(details=str(err)) from err

        if actual_size != file_upload.encrypted_size:
            file_upload.state = "failed"
            file_upload.state_updated = now_utc_ms_prec()
            file_upload.failure_reason = "Actual object size didn't match expected size"
            await self._file_upload_dao.update(file_upload)
            error = self.UploadSizeMismatchError(file_id=file_id)
            log.error(
                error,
                extra={
                    "bucket_id": file_upload.bucket_id,
                    "file_id": file_id,
                    "object_id": object_id,
                    "expected_size": file_upload.encrypted_size,
                    "actual_size": actual_size,
                },
            )
            raise error

    async def complete_file_upload(  # noqa: PLR0913
        self,
        *,
        box_id: UUID4,
        file_id: UUID4,
        unencrypted_checksum: str,
        encrypted_checksum: str,
        encrypted_parts_md5: list[str],
        encrypted_parts_sha256: list[str],
    ) -> None:
        """Instruct S3 to complete a multipart upload and compares the remote checksum
        with the value provided for `encrypted_checksum`. The `unencrypted_checksum`
        is stored in the database.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `BoxNotFoundError` if the FileUploadBox isn't found.
        - `BoxStateError` if the box exists but is locked.
        - `BoxVersionError` if the box version changed before stats could be updated.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadCompletionError` if there's an error while telling S3 to complete the upload.
        - `UploadSizeMismatchError` if the object size doesn't match the declared encrypted_size.
        - `ChecksumMismatchError` if the checksums don't match.
        """
        # Get the FileUploadBox instance and verify that it is unlocked
        box = await self._get_unlocked_box(box_id=box_id)
        box_version = box.version
        extra: dict[str, Any] = {"box_id": box_id, "file_id": file_id}  # just 4 logging

        # Get the FileUpload from the DB
        try:
            file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.FileUploadNotFound(file_id=file_id)
            log.error(error, extra=extra)
            raise error from err

        if file_upload.state in ("cancelled", "failed"):
            error = self.FileUploadStateError(
                file_id=file_id,
                details=f"Cannot complete a FileUpload in the '{file_upload.state}' state.",
            )
            log.error(error, extra=extra)
            raise error

        # Exit early if the FileUpload is complete (already in the inbox or archived)
        if file_upload.state != "init":
            log.info("FileUpload with ID %s already complete.", file_id)
            return

        try:
            await self._s3_client.complete_multipart_upload(file_upload=file_upload)
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=file_upload.storage_alias
            ) from err
        except S3ClientPort.S3UploadCompletionError as err:
            raise self.UploadCompletionError(
                file_id=file_id,
                s3_upload_id=file_upload.s3_upload_id,
                bucket_id=file_upload.bucket_id,
            ) from err
        except S3ClientPort.BucketNotFoundError as err:
            raise self.BucketMissingError(bucket_id=file_upload.bucket_id) from err
        except S3ClientPort.S3OperationError as err:
            raise self.S3OperationError(details=str(err)) from err

        # Verify that the md5 checksum calculated by the connector matches the S3 etag
        await self._compare_checksums(
            file_upload=file_upload,
            expected_checksum=encrypted_checksum,
        )

        # Verify that the actual object size matches the declared encrypted_size
        await self._verify_object_size(file_upload=file_upload)

        # Update local collections now that S3 upload is successfully completed
        file_upload.state = "inbox"
        file_upload.decrypted_sha256 = unencrypted_checksum
        file_upload.encrypted_parts_md5 = encrypted_parts_md5
        file_upload.encrypted_parts_sha256 = encrypted_parts_sha256
        file_upload.state_updated = now_utc_ms_prec()
        file_upload.completed = now_utc_ms_prec()
        await self._file_upload_dao.update(file_upload)

        # Delete the upload activity entry now that the upload is in the inbox
        try:
            await self._upload_activity_dao.delete(file_id)
        except ResourceNotFoundError:
            log.warning(
                "Activity entry not found when completing upload for file %s.", file_id
            )

        # Update the FileUploadBox with new size and file count
        await self._update_box_stats(box_id=box_id, version=box_version)
        log.info("DB data updated for upload completion of file %s", file_id)

    async def remove_file_upload(self, *, box_id: UUID4, file_id: UUID4) -> None:
        """Remove a file upload and cancel the ongoing upload if applicable.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `BoxStateError` if the box exists but is locked.
        - `BoxVersionError` if the box version changed before stats could be updated.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        # Make sure box exists and is unlocked (unless overridden)
        box = await self._get_unlocked_box(box_id=box_id)

        # Retrieve the FileUpload data
        try:
            file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.FileUploadNotFound(file_id=file_id)
            log.error(error)
            raise error from err

        # Remove the file from S3 only if it's still in the inbox state. After that
        #  point, the bucket ID and object ID will refer to another bucket for which UCS
        #  has no write access.
        if file_upload.state == "inbox":
            await self._remove_completed_file_upload(file_upload=file_upload)
        # Abort the upload if it still hasn't completed
        elif file_upload.state == "init":
            await self._remove_incomplete_file_upload(file_upload=file_upload)

        # Update the file_upload to 'cancelled'
        file_upload.state = "cancelled"
        file_upload.state_updated = now_utc_ms_prec()
        await self._file_upload_dao.update(file_upload)

        # Delete the upload activity entry
        with contextlib.suppress(ResourceNotFoundError):
            await self._upload_activity_dao.delete(file_id)

        await self._update_box_stats(box_id=box_id, version=box.version)
        log.info("File %s deleted from box %s", file_id, box_id)

    async def remove_file_upload_box(
        self, *, box_id: UUID4, version: int | None = None
    ) -> None:
        """Remove a FileUploadBox and delete all associated FileUploads.

        If `version` is provided, it must match the box's current version.
        The box is locked before its FileUploads are swept so no new uploads
        can be initiated mid-deletion.

        Files in 'init' state have their S3 multipart upload aborted.
        Files in 'inbox' state have their S3 object deleted.
        Files in other states require no S3 interaction.
        Files in 'awaiting_archival' or 'archived' state cause a FileUploadStateError
        (invariant violation: these states require the box to be archived).

        All FileUpload documents belonging to the box are hard-deleted, emitting
        'deleted' outbox events.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `BoxVersionError` if a version is supplied and doesn't match the current one.
        - `BoxStateError` if the box is archived.
        - `FileUploadStateError` if any FileUpload is in 'awaiting_archival' or 'archived' state.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error aborting an in-progress multipart upload.
        """
        # Get the box
        try:
            box = await self._file_upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.BoxNotFoundError(box_id=box_id)
            log.error(error)
            raise error from err

        # Verify the version
        if version is not None and box.version != version:
            error = self.BoxVersionError(box_id=box_id)
            log.error(error, extra={"box_id": box_id, "version": version})
            raise error

        # Raise an error if the box is archived
        if box.state == "archived":
            error = self.BoxStateError(box_id=box_id, box_state=box.state)
            log.error(error)
            raise error

        # Lock the box so no new uploads can be initiated while sweeping
        if box.state == "open":
            box.version += 1
            box.state = "locked"
            await self._file_upload_box_dao.update(box)
            log.info("Locked FileUploadBox %s before deleting files.", box_id)

        # Before deleting anything, make sure there aren't any FileUploads in an
        #  unexpected state. Raising an error here leaves the box in the locked state,
        #  which should be fine because it doesn't prevent a subsequent deletion attempt
        files_with_wrong_state = [
            x
            async for x in self._file_upload_dao.find_all(
                mapping={
                    "box_id": box_id,
                    "state": {"$in": ["awaiting_archival", "archived"]},
                }
            )
        ]

        if files_with_wrong_state:
            first_bad_file = files_with_wrong_state[0]
            error = self.FileUploadStateError(
                file_id=first_bad_file.id,
                details=(
                    f"FileUpload {first_bad_file.id} is in the '{first_bad_file.state}',"
                    + " state which should only be reachable when the box is archived."
                    + " This indicates a data inconsistency."
                ),
            )
            log.error(
                error,
                extra={
                    "box_id": box_id,
                    "files_with_wrong_state": [f.id for f in files_with_wrong_state],
                },
            )
            raise error

        # Delete the FileUploads
        await self._delete_box_file_uploads(box_id=box_id)

        # Finally, delete the box itself
        await self._file_upload_box_dao.delete(box_id)
        log.info("Deleted FileUploadBox %s.", box_id)

    async def _delete_box_file_uploads(self, *, box_id: UUID4) -> None:
        """Hard-delete all FileUploads belonging to a box after S3 cleanup.

        Sweeps until clean: initiation requests in flight before the box was locked
        may still insert FileUploads after a pass completes; the lock guarantees the
        loop terminates because no new initiations can begin.

        Raises:
        - `UnknownStorageAliasError` if a storage alias is not known.
        - `UploadAbortError` if there's an error aborting an in-progress multipart upload.
        """
        while True:
            file_uploads = [
                upload
                async for upload in self._file_upload_dao.find_all(
                    mapping={"box_id": box_id}
                )
            ]
            if not file_uploads:
                log.info("Deleted all FileUploads for FileUploadBox %s.", box_id)
                break

            log.debug("Deleting all FileUploads for FileUploadBox %s.", box_id)
            for file_upload in file_uploads:
                if file_upload.state == "inbox":
                    await self._remove_completed_file_upload(file_upload=file_upload)
                elif file_upload.state == "init":
                    await self._remove_incomplete_file_upload(file_upload=file_upload)

                with contextlib.suppress(ResourceNotFoundError):
                    await self._upload_activity_dao.delete(file_upload.id)
                await self._file_upload_dao.delete(file_upload.id)

    async def _update_box_stats(self, *, box_id: UUID4, version: int) -> None:
        """Update FileUploadBox stats (file count & size) in an idempotent manner,
        counting only files that are finished uploading.

        Re-fetches the box to get the latest state, verifies the version is still
        current before applying any changes.

        This helps mitigate potential state inconsistency arising from a hard crash.

        Raises:
        - `BoxNotFoundError` if the box no longer exists.
        - `BoxVersionError` if the box version has changed since it was fetched.
        """
        box = await self._get_box_at_version(box_id=box_id, version=version)

        file_count = 0
        total_size = 0
        async for file_upload in self._file_upload_dao.find_all(
            mapping={
                "box_id": box_id,
                "state": {
                    "$in": ["inbox", "interrogated", "awaiting_archival", "archived"]
                },
            }
        ):
            file_count += 1
            total_size += file_upload.decrypted_size

        # Since every update triggers an event, only update if data differs
        if file_count != box.file_count or total_size != box.size:
            box.version += 1
            box.file_count = file_count
            box.size = total_size
            await self._file_upload_box_dao.update(box)

    async def create_file_upload_box(
        self, *, storage_alias: str, max_size: int
    ) -> UUID4:
        """Create a new FileUploadBox with the given S3 storage alias.
        Returns the UUID4 id of the created FileUploadBox.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        """
        if storage_alias not in self._config.object_storages:
            raise self.UnknownStorageAliasError(storage_alias=storage_alias)

        box = FileUploadBox(
            id=uuid4(),
            version=0,
            state="open",
            file_count=0,
            size=0,
            max_size=max_size,
            storage_alias=storage_alias,
        )
        await self._file_upload_box_dao.insert(box)
        log.debug(
            "Inserted FileUploadBox %s", box.id, extra={"storage_alias": storage_alias}
        )
        return box.id

    async def update_box_max_size(
        self, *, box_id: UUID4, version: int, max_size: int
    ) -> None:
        """Update the max_size of an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `BoxMaxSizeTooLowError` if the new max_size is smaller than what has
            already been uploaded.
        """
        box = await self._get_box_at_version(box_id=box_id, version=version)

        if max_size < box.size:
            error = self.BoxMaxSizeTooLowError(
                box_id=box_id, max_size=max_size, current_size=box.size
            )
            log.error(error, extra={"box_id": box_id, "max_size": max_size})
            raise error

        box.version += 1
        box.max_size = max_size
        await self._file_upload_box_dao.update(box)
        log.info("Updated max_size for box %s to %s.", box_id, max_size)

    async def lock_file_upload_box(
        self, *, box_id: UUID4, version: int, force: bool = False
    ) -> None:
        """Lock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `IncompleteUploadsError` if force is False and the box has incomplete FileUploads.
        - `UploadAbortError` if force is True and aborting an in-progress upload fails.
        """
        box = await self._get_box_at_version(box_id=box_id, version=version)

        if box.state != "open":
            # This goes for archived boxes too
            log.info("Box with ID %s is already locked.", box_id)
            return

        incomplete_files = [
            upload
            async for upload in self._file_upload_dao.find_all(
                mapping={"box_id": box_id, "state": "init"}
            )
        ]

        if force:
            for upload in incomplete_files:
                await self._remove_incomplete_file_upload(file_upload=upload)
                upload.state = "cancelled"
                upload.state_updated = now_utc_ms_prec()
                await self._file_upload_dao.update(upload)
                with contextlib.suppress(ResourceNotFoundError):
                    await self._upload_activity_dao.delete(upload.id)
            if incomplete_files:
                log.info(
                    "Aborted %d in-progress upload(s) in box %s for forced lock.",
                    len(incomplete_files),
                    box_id,
                )
        else:
            file_ids = sorted(
                [(x.id, x.alias) for x in incomplete_files],
                key=lambda entry: entry[1],
            )
            if file_ids:
                error = self.IncompleteUploadsError(box_id=box_id, file_ids=file_ids)
                log.error(error, extra={"box_id": box_id, "file_ids": str(file_ids)})
                raise error

        box.version += 1
        box.state = "locked"
        await self._file_upload_box_dao.update(box)
        log.info("Locked box with ID %s.", box_id)

    async def unlock_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Unlock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `BoxStateError` if the box is archived and cannot be unlocked.
        """
        box = await self._get_box_at_version(box_id=box_id, version=version)

        if box.state == "locked":
            box.version += 1
            box.state = "open"
            await self._file_upload_box_dao.update(box)
            log.info("Unlocked box with ID %s", box_id)
        elif box.state == "archived":
            log.error("Can't unlock box %s because it's already archived.", box_id)
            raise self.BoxStateError(box_id=box_id, box_state=box.state)
        else:
            log.info("Box with ID %s is already unlocked", box_id)

    async def archive_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Archive an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `BoxStateError` if the box is open.
        - `IncompleteUploadsError` if the FileUploadBox has incomplete FileUploads.
        - `FileArchivalError` if there's a problem archiving a given FileUpload.
        """
        box = await self._get_box_at_version(box_id=box_id, version=version)

        # Exit early if already archived, or raise error if unlocked
        if box.state == "archived":
            log.info("Box with ID %s is already archived", box_id)
            return
        elif box.state == "open":
            log.error("Can't unlock box %s because it's still open.", box_id)
            raise self.BoxStateError(box_id=box_id, box_state=box.state)

        # Scan for incomplete files
        files_not_interrogated_cursor = self._file_upload_dao.find_all(
            mapping={"box_id": box_id, "state": {"$in": ["init", "inbox"]}}
        )
        file_ids = sorted(
            [(x.id, x.alias) async for x in files_not_interrogated_cursor],
            key=lambda entry: entry[1],
        )
        if file_ids:
            error = self.IncompleteUploadsError(box_id=box_id, file_ids=file_ids)
            log.error(error, extra={"box_id": box_id, "file_ids": str(file_ids)})
            raise error

        # Verify that all files are in state 'interrogated' or 'awaiting_archival'.
        # We include the latter in case an early crash occurred after partial update
        files_cursor = self._file_upload_dao.find_all(
            mapping={
                "box_id": box_id,
                "state": {"$in": ["interrogated", "awaiting_archival"]},
            }
        )
        async for file in files_cursor:
            # Check certain FileUpload fields one last time
            if (
                not file.encrypted_parts_md5
                or not file.encrypted_parts_sha256
                or len(file.encrypted_parts_md5) != len(file.encrypted_parts_sha256)
            ):
                raise self.FileArchivalError(
                    f"File part checksums appear corrupted for file {file.id}."
                )
            elif file.failure_reason:
                raise self.FileArchivalError(
                    f"The 'failure_reason' for file {file.id} is unexpectedly filled out."
                )
            file.state = "awaiting_archival"
            file.state_updated = now_utc_ms_prec()
            await self._file_upload_dao.update(file)

        # Update the box last
        box.version += 1
        box.state = "archived"
        await self._file_upload_box_dao.update(box)
        log.info("Archived box with ID %s", box_id)

    async def get_box_file_info(self, *, box_id: UUID4) -> list[FileUpload]:
        """Return the list of FileUploads for a FileUploadBox, sorted by alias.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        """
        try:
            # assert the box exists
            _ = await self._file_upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.BoxNotFoundError(box_id=box_id)
            log.error(error)
            raise error from err

        # Box exists, now get all file uploads
        file_uploads = [
            x async for x in self._file_upload_dao.find_all(mapping={"box_id": box_id})
        ]
        file_uploads.sort(key=lambda x: x.alias)
        return file_uploads

    async def process_interrogation_success(
        self, *, report: InterrogationSuccess
    ) -> None:
        """Update a FileUpload with the information from a corresponding successful
        interrogation report and remove it from the inbox bucket.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        file_id = report.file_id
        try:
            old_file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.FileUploadNotFound(file_id=file_id)
            log.error(error, extra={"file_id": file_id})
            raise error from err

        match old_file_upload.state:
            case "init":
                log.warning(
                    "Ignoring interrogation report for FileUpload %s since it is still"
                    + " in the 'init' state.",
                    file_id,
                )
                return
            case "inbox":
                # Update the FileUpload's parameters using the InterrogationReport
                await self._remove_completed_file_upload(file_upload=old_file_upload)
                updated_file_upload = old_file_upload.model_copy(deep=True)
                updated_file_upload.state = "interrogated"
                updated_file_upload.state_updated = now_utc_ms_prec()
                updated_file_upload.secret_id = report.secret_id
                updated_file_upload.encrypted_parts_md5 = report.encrypted_parts_md5
                updated_file_upload.encrypted_parts_sha256 = (
                    report.encrypted_parts_sha256
                )
                updated_file_upload.bucket_id = report.bucket_id
                updated_file_upload.object_id = report.object_id
                updated_file_upload.encrypted_size = report.encrypted_size
                log.debug(
                    "Marking FileUpload %s as '%s'", file_id, updated_file_upload.state
                )
                await self._file_upload_dao.update(updated_file_upload)
            case _:
                log.info(
                    "FileUpload %s was already marked as '%s', so it's likely"
                    + " this interrogation report has been processed already.",
                    file_id,
                    old_file_upload.state,
                )

    async def process_interrogation_failure(
        self, *, report: InterrogationFailure
    ) -> None:
        """Update a FileUpload state to 'failed' and remove it from the inbox bucket.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        file_id = report.file_id
        try:
            file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.FileUploadNotFound(file_id=file_id)
            log.error(error, extra={"file_id": file_id})
            raise error from err

        match file_upload.state:
            case "init":
                log.warning(
                    "Ignoring interrogation failure report for FileUpload %s since it"
                    + " is still in the 'init' state.",
                    file_id,
                )
                return
            case "inbox":
                await self._remove_completed_file_upload(file_upload=file_upload)
                file_upload.state = "failed"
                file_upload.state_updated = now_utc_ms_prec()
                file_upload.failure_reason = report.reason
                log.debug("Marking FileUpload %s as '%s'", file_id, file_upload.state)
                await self._file_upload_dao.update(file_upload)
            case _:
                log.info(
                    "FileUpload %s was already marked as '%s', so it's likely"
                    + " this interrogation failure report has been processed already.",
                    file_id,
                    file_upload.state,
                )

    async def process_internal_file_registration(
        self, *, registration_metadata: FileInternallyRegistered
    ) -> None:
        """Update a FileUpload state to 'archived' and verify other data.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `FileUploadStateError` if the FileUpload's details aren't what's expected.
        """
        file_id = registration_metadata.file_id
        try:
            file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.FileUploadNotFound(file_id=file_id)
            log.error(error, extra={"file_id": file_id})
            raise error from err

        if file_upload.state == "archived":
            log.info("FileUpload %s is already marked 'archived', returning.", file_id)
            return

        if file_upload.state != "awaiting_archival":
            details = f"FileUpload state was {file_upload.state}, but expected 'awaiting_archival'."
            error = self.FileUploadStateError(file_id=file_id, details=details)
            log.error(error)
            raise error

        # Update the state and state_updated fields
        file_upload.state = "archived"
        file_upload.state_updated = now_utc_ms_prec()

        for field in [
            "decrypted_sha256",
            "encrypted_parts_md5",
            "encrypted_parts_sha256",
            "storage_alias",
            "secret_id",
            "decrypted_size",
            "encrypted_size",
        ]:
            if getattr(file_upload, field) != getattr(registration_metadata, field):
                details = f"The value for {field} doesn't match the event data."
                error = self.FileUploadStateError(file_id=file_id, details=details)
                log.error(error)
                raise error

        await self._file_upload_dao.update(file_upload)
        log.info("Processed internal file registration for %s.", file_id)

    async def process_file_deletion_requested(self, *, file_id: UUID4) -> None:
        """Process a deletion request for the given FileUpload ID.

        This will remove the object from the inbox, if it exists.
        Database objects are untouched.

        If no FileUpload with the given ID exists, merely logs a warning and returns.
        """
        try:
            file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError:
            log.warning(
                "Cannot process deletion request for file ID %s. No such FileUpload found.",
                file_id,
                extra={"file_id": file_id},
            )
            return

        if file_upload.state in ["cancelled", "failed"]:
            log.info(
                "FileUpload %s is already marked '%s', further action presumed unnecessary.",
                file_id,
                file_upload.state,
            )
            return

        # This will result in a second FileUpload fetch, but alternative is to
        #  replicate removal logic here
        await self.remove_file_upload(box_id=file_upload.box_id, file_id=file_id)

    async def cleanup_stale_uploads(self) -> None:
        """Abort stale in-progress multipart uploads and mark their FileUpload records
        as 'cancelled'. Also aborts any orphaned S3 multipart uploads that have no
        corresponding FileUpload record.

        An upload is considered stale if its last-activity timestamp is older than
        `config.multipart_upload_ttl_hours` hours. If no activity entry exists,
        falls back to comparing the FileUpload's `initiated` timestamp.
        """
        cutoff = now_utc_ms_prec() - timedelta(
            hours=self._config.multipart_upload_ttl_hours
        )
        for storage_alias in self._config.object_storages:
            await self._cleanup_stale_uploads_for_alias(
                storage_alias=storage_alias, cutoff=cutoff
            )

    async def _find_stale_uploads(
        self,
        *,
        ongoing_uploads: list[FileUpload],
        cutoff: UTCDatetime,
    ) -> list[FileUpload]:
        """Return uploads from ongoing_uploads whose last activity is older than cutoff.

        Falls back to the upload's `initiated` timestamp when no activity entry exists.
        """
        stale_uploads: list[FileUpload] = []
        mapping = {"file_id": {"$in": [file.id for file in ongoing_uploads]}}
        activities = {
            activity.file_id: activity.last_activity
            async for activity in self._upload_activity_dao.find_all(mapping=mapping)
        }

        for upload in ongoing_uploads:
            try:
                if activities[upload.id] <= cutoff:
                    stale_uploads.append(upload)
            except KeyError:
                log.debug(
                    "FileUpload %s did not have a matching upload activity entry, so"
                    + " the initiated date of %s was referenced instead.",
                    upload.id,
                    upload.initiated.isoformat(),
                    extra={"cutoff": cutoff},
                )
                if upload.initiated <= cutoff:
                    stale_uploads.append(upload)
        return stale_uploads

    async def _cancel_stale_file_upload(
        self, *, upload: FileUpload, storage_alias: str
    ) -> None:
        """Abort the S3 multipart upload and mark the FileUpload as 'cancelled'."""
        try:
            await self._remove_incomplete_file_upload(file_upload=upload)
        except Exception:
            # If there's a problem aborting the stale upload, log it but otherwise go on
            log.error(
                "Failed to abort S3 upload for stale file %s in alias '%s'.",
                upload.id,
                storage_alias,
                exc_info=True,
            )

        # Update FileUpload as cancelled regardless of whether S3 upload was aborted -
        #  the next round of cleanup will catch it
        upload.state = "cancelled"
        upload.state_updated = now_utc_ms_prec()
        await self._file_upload_dao.update(upload)
        with contextlib.suppress(ResourceNotFoundError):
            await self._upload_activity_dao.delete(upload.id)
        log.info("Cleaned up stale upload %s (alias '%s')", upload.id, storage_alias)

    async def _abort_orphaned_s3_uploads(
        self,
        *,
        storage_alias: str,
        orphaned_s3_uploads: dict[str, str],
    ) -> None:
        """Abort S3 multipart uploads that have no corresponding FileUpload record."""
        for s3_upload_id, object_id in orphaned_s3_uploads.items():
            try:
                await self._s3_client.abort_multipart_upload(
                    storage_alias=storage_alias,
                    object_id=object_id,
                    s3_upload_id=s3_upload_id,
                )
            except Exception:
                log.exception(
                    "Failed to abort orphaned S3 upload %s (object %s) for alias '%s'.",
                    s3_upload_id,
                    object_id,
                    storage_alias,
                )

    async def _cleanup_stale_uploads_for_alias(
        self,
        *,
        storage_alias: str,
        cutoff: UTCDatetime,
    ) -> None:
        """Run stale upload cleanup for a single storage alias.

        This aborts ongoing uploads that are too old or not tied to any FileUpload.
        Orphaned objects are also deleted.
        """
        # Fetch all FileUploads for this storage alias that are still 'init' or 'inbox'
        #  to avoid doing a second query later when performing object cleanup
        init_and_inbox_uploads = [
            upload
            async for upload in self._file_upload_dao.find_all(
                mapping={
                    "storage_alias": storage_alias,
                    "state": {"$in": ["init", "inbox"]},
                }
            )
        ]

        # Get just the 'init', i.e. ongoing, uploads from that list
        ongoing_uploads = [x for x in init_and_inbox_uploads if x.state == "init"]
        known_init_object_ids = {str(upload.object_id) for upload in ongoing_uploads}

        # Determine which of the ongoing uploads have been dormant since the cutoff time
        stale_uploads = await self._find_stale_uploads(
            ongoing_uploads=ongoing_uploads, cutoff=cutoff
        )

        # Get all active S3 multipart uploads in this storage's inbox bucket so we can
        #  look for stale uploads that might have been abandoned due to errors or other
        #  processes that orphaned them from any database records.
        try:
            active_s3_uploads = await self._s3_client.list_all_multipart_uploads(
                storage_alias=storage_alias
            )
        except S3ClientPort.UnknownStorageAliasError:
            log.error(
                "Unknown storage alias '%s' during stale upload cleanup.", storage_alias
            )
            raise
        except Exception:
            log.error(
                "Failed to list S3 multipart uploads for alias '%s'.", storage_alias
            )
            raise

        # Find truly orphaned S3 uploads (object_id not matching any known init FileUpload)
        orphaned_s3_uploads = {
            s3_upload_id: object_id
            for s3_upload_id, object_id in active_s3_uploads.items()
            if object_id not in known_init_object_ids
        }

        # Cancel each of the stale uploads that have FileUpload entries in the DB
        for upload in stale_uploads:
            await self._cancel_stale_file_upload(
                upload=upload, storage_alias=storage_alias
            )

        await self._abort_orphaned_s3_uploads(
            storage_alias=storage_alias, orphaned_s3_uploads=orphaned_s3_uploads
        )

        # Get a set of all object_ids from init_and_inbox_uploads. Cast to str because
        #  S3Client does a set diff on the string object IDs returned by S3
        known_object_ids = {str(x.object_id) for x in init_and_inbox_uploads}
        await self._s3_client.cleanup_orphaned_objects(
            storage_alias=storage_alias, known_object_ids=known_object_ids
        )
