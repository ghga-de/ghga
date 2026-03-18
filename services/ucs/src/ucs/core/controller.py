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

"""Implements the UploadController class to manage file uploads"""

import logging
from contextlib import suppress
from typing import Any
from uuid import uuid4

from ghga_event_schemas.pydantic_ import (
    FileInternallyRegistered,
    InterrogationFailure,
    InterrogationSuccess,
)
from hexkit.protocols.dao import NoHitsFoundError, UniqueConstraintViolationError
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from ucs.config import Config
from ucs.core.models import FileUpload, FileUploadBox, S3UploadDetails
from ucs.ports.inbound.controller import UploadControllerPort
from ucs.ports.outbound.dao import (
    FileUploadBoxDao,
    FileUploadDao,
    ResourceNotFoundError,
    S3UploadDetailsDao,
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
        s3_upload_details_dao: S3UploadDetailsDao,
        s3_client: S3ClientPort,
    ):
        self._config = config
        self._file_upload_box_dao = file_upload_box_dao
        self._file_upload_dao = file_upload_dao
        self._s3_upload_details_dao = s3_upload_details_dao
        self._s3_client = s3_client

    async def _insert_file_upload_if_new(  # noqa: PLR0913
        self,
        *,
        box: FileUploadBox,
        alias: str,
        bucket_id: str,
        decrypted_size: int,
        encrypted_size: int,
        part_size: int,
    ) -> FileUpload:
        """Create a new FileUpload for the provided file alias and return it.

        This method tries to insert a new FileUpload with random UUID4s for file_id
        and object_id.

        Raises `FileUploadAlreadyExists` if there's already a FileUpload for this alias
        and box_id.
        """
        box_id = box.id
        file_id = uuid4()
        object_id = uuid4()

        try:
            file_upload = FileUpload(
                id=file_id,
                box_id=box_id,
                alias=alias,
                state="init",
                state_updated=now_utc_ms_prec(),
                storage_alias=box.storage_alias,
                bucket_id=bucket_id,
                object_id=object_id,
                decrypted_size=decrypted_size,
                encrypted_size=encrypted_size,
                part_size=part_size,
            )

            await self._file_upload_dao.insert(file_upload)
            return file_upload
        except UniqueConstraintViolationError as err:
            # If there's already a FileUpload in the box with this alias, retrieve it
            try:
                existing_upload = await self._file_upload_dao.find_one(
                    mapping={"box_id": box_id, "alias": alias}
                )
            except NoHitsFoundError:
                # If we don't get any hits, something weird is going on. This isn't a
                #  typical error to handle, so raise a RuntimeError
                msg = (
                    "Encountered an error indicating this FileUploadBox already"
                    + f" has a FileUpload for the alias {alias}, but got no results"
                    + " when trying to retrieve the existing FileUpload."
                )
                error = RuntimeError(msg)
                log.critical(error, extra={"box_id": box.id, "file_alias": alias})
                raise error from err

            # If retrieval succeeds, evaluate and attempt to replace the file upload
            logging_extras = {  # only for logging
                "box_id": box.id,
                "file_alias": file_upload.alias,
                "old_file_upload_id": existing_upload.id,
                "old_state": existing_upload.state,
                "new_file_upload_id": file_upload.id,
            }
            replaced = await self._try_to_replace_upload(
                box=box,
                existing_upload=existing_upload,
                new_upload=file_upload,
                logging_extras=logging_extras,
            )
            if not replaced:
                error = self.FileUploadAlreadyExists(alias=alias)
                log.error(error, extra=logging_extras)
                raise error from err

            # If successful, return the new file upload instance
            return file_upload

    async def _try_to_replace_upload(
        self,
        box: FileUploadBox,
        existing_upload: FileUpload,
        new_upload: FileUpload,
        logging_extras: dict[str, Any],
    ) -> bool:
        """Try to replace an existing FileUpload for a given box and alias.

        If successful, this method will delete any existing S3UploadDetails from the
        database, delete the old FileUpload, and insert the new one.
        This does result in an outbox deletion event for the old FileUpload.

        Returns a boolean indicating whether replacement was successful.
        """
        # Examine the existing FileUpload - it has to be either failed or cancelled to
        #  be replaced with the new submission. If not, we have to raise an error.
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
        # Make sure to delete S3UploadDetails for the old FileUpload and log it
        with suppress(ResourceNotFoundError):
            await self._s3_upload_details_dao.delete(existing_upload.id)
            log.info(
                "Cleaned out S3UploadDetails for old, %s FileUpload %s because it"
                + " is being superseded by FileUpload %s.",
                existing_upload.state,
                existing_upload.id,
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

    async def _remove_completed_file_upload(
        self, *, s3_upload_details: S3UploadDetails
    ) -> None:
        """Delete a completely uploaded file from S3 or abort any stale multipart.

        Does not delete any data from the DB.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
          If this occurs, developer intervention might be required.
        """
        try:
            await self._s3_client.delete_inbox_file(s3_upload_details=s3_upload_details)
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=s3_upload_details.storage_alias
            ) from err
        except S3ClientPort.S3UploadAbortError as err:
            raise self.UploadAbortError(
                file_id=s3_upload_details.file_id,
                s3_upload_id=s3_upload_details.s3_upload_id,
                bucket_id=s3_upload_details.bucket_id,
            ) from err

    async def _remove_incomplete_file_upload(
        self, *, s3_upload_details: S3UploadDetails
    ) -> None:
        """Abort an incomplete S3 multipart upload.

        Does not delete any data from the DB.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        try:
            await self._s3_client.abort_multipart_upload(
                s3_upload_details=s3_upload_details
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=s3_upload_details.storage_alias
            ) from err
        except S3ClientPort.S3UploadAbortError as err:
            raise self.UploadAbortError(
                file_id=s3_upload_details.file_id,
                s3_upload_id=s3_upload_details.s3_upload_id,
                bucket_id=s3_upload_details.bucket_id,
            ) from err

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
        - `FileUploadAlreadyExists` if there's already a FileUpload for this alias.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAlreadyInProgressError` if an upload is already in progress.
        """
        extra: dict[str, Any] = {"box_id": box_id, "alias": alias}
        # Get the box and create the FileUpload
        box = await self._get_unlocked_box(box_id=box_id)

        # Get the S3 storage details
        storage_alias = box.storage_alias
        try:
            bucket_id = self._s3_client.get_bucket_id_for_alias(
                storage_alias=storage_alias
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(storage_alias=storage_alias) from err
        extra["storage_alias"] = storage_alias
        extra["bucket_id"] = bucket_id

        initiated = now_utc_ms_prec()  # Generate timestamp early to minimize error risk
        file_upload = await self._insert_file_upload_if_new(
            box=box,
            alias=alias,
            bucket_id=bucket_id,
            decrypted_size=decrypted_size,
            encrypted_size=encrypted_size,
            part_size=part_size,
        )
        file_id = file_upload.id
        object_id = file_upload.object_id
        log.info("FileUpload %s added for alias %s.", file_id, alias, extra=extra)

        # Initiate a new multipart file upload on the S3 instance
        try:
            s3_upload_id = await self._s3_client.init_multipart_upload(
                file_upload=file_upload
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(storage_alias=storage_alias) from err
        except S3ClientPort.OrphanedMultipartUploadError as err:
            #  _insert_file_upload_if_new precludes the existence of a FileUpload
            #  with the same `file_id`. If there's no FileUpload with the same file_id,
            #  then there cannot be an upload for said file_id. Since each FileUpload
            #  gets a freshly generated object_id, a collision here would be extremely
            #  unlikely. The most likely cause is a crash between creating the S3 upload
            #  and inserting the S3UploadDetails. We can't assign S3 upload IDs, so if
            #  that data isn't saved to the DB, it is only preserved in the logs. There
            #  is no straightforward way to get the upload ID programmatically, so we
            #  can't auto-abort it, either. In this case someone will have to
            #  manually intervene to cancel the upload. We will delete the FileUpload,
            #  however, so the user can immediately retry.
            log.critical(str(err), extra=extra)
            await self._file_upload_dao.delete(file_id)
            log.info("Cleanup performed - FileUpload %s deleted.", file_id)
            raise self.UploadAlreadyInProgressError(
                file_id=file_id, bucket_id=bucket_id
            ) from err

        # Insert S3UploadDetails. Don't check for duplicate because insert only
        #  occurs in this method and only if the FileUpload alias is new. The check for
        #  duplicates is performed in `_insert_validated_file_upload`.
        s3_upload = S3UploadDetails(
            file_id=file_id,
            storage_alias=storage_alias,
            bucket_id=bucket_id,
            object_id=object_id,
            s3_upload_id=s3_upload_id,
            initiated=initiated,
        )
        await self._s3_upload_details_dao.insert(s3_upload)
        log.info(
            "FileUpload object with ID %s created for file alias %s. The S3 multipart"
            + " upload ID is %s.",
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
        - `S3UploadDetailsNotFoundError` if no upload details are found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadSessionNotFoundError` if the upload session can't be found.
        """
        # Retrieve the S3Upload record for this file ID
        try:
            s3_upload_details = await self._s3_upload_details_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.S3UploadDetailsNotFoundError(file_id=file_id)
            log.error(
                error,
                extra={"file_id": file_id, "part_no": part_no},
            )
            raise error from err

        s3_upload_id = s3_upload_details.s3_upload_id
        try:
            return await self._s3_client.get_part_upload_url(
                s3_upload_details=s3_upload_details, part_no=part_no
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=s3_upload_details.storage_alias
            ) from err
        except S3ClientPort.S3UploadNotFoundError as err:
            log.error(
                err,
                extra={
                    "s3_upload_id": s3_upload_id,
                    "file_id": file_id,
                    "bucket_id": s3_upload_details.bucket_id,
                    "part_no": part_no,
                    "storage_alias": s3_upload_details.storage_alias,
                },
            )
            raise self.UploadSessionNotFoundError(
                bucket_id=s3_upload_details.bucket_id, s3_upload_id=s3_upload_id
            ) from err

    async def _compare_checksums(
        self,
        s3_upload_details: S3UploadDetails,
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
                s3_upload_details=s3_upload_details, object_id=object_id
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=s3_upload_details.storage_alias
            ) from err

        if actual_checksum != expected_checksum:
            # Mark upload as failed, then raise an error
            file_upload.state = "failed"
            file_upload.state_updated = now_utc_ms_prec()
            file_upload.failure_reason = "Upload integrity checksum mismatch"
            await self._file_upload_dao.update(file_upload)
            log.info("Marked FileUpload %s as 'failed'.", file_id)
            error = self.ChecksumMismatchError(file_id=file_id)
            extra = {
                "bucket_id": s3_upload_details.bucket_id,
                "file_id": file_id,
                "object_id": object_id,
                "expected_checksum": expected_checksum,
                "actual_checksum": actual_checksum,
            }
            log.error(error, extra=extra)
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
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
        - `BoxNotFoundError` if the FileUploadBox isn't found.
        - `BoxStateError` if the box exists but is locked.
        - `BoxVersionError` if the box version changed before stats could be updated.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadCompletionError` if there's an error while telling S3 to complete the upload.
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

        # Get s3 upload details
        try:
            s3_upload_details = await self._s3_upload_details_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.S3UploadDetailsNotFoundError(file_id=file_id)
            log.error(error, extra=extra)
            raise error from err

        # Exit early if the FileUpload is complete (already in the inbox or archived)
        if file_upload.inbox_upload_completed:
            log.info("FileUpload with ID %s already complete.", file_id)
            return

        try:
            await self._s3_client.complete_multipart_upload(
                s3_upload_details=s3_upload_details
            )
        except S3ClientPort.UnknownStorageAliasError as err:
            raise self.UnknownStorageAliasError(
                storage_alias=s3_upload_details.storage_alias
            ) from err
        except S3ClientPort.S3UploadCompletionError as err:
            raise self.UploadCompletionError(
                file_id=file_id,
                s3_upload_id=s3_upload_details.s3_upload_id,
                bucket_id=s3_upload_details.bucket_id,
            ) from err

        # Verify that the md5 checksum calculated by the connector matches the S3 etag
        await self._compare_checksums(
            s3_upload_details=s3_upload_details,
            file_upload=file_upload,
            expected_checksum=encrypted_checksum,
        )

        # Update local collections now that S3 upload is successfully completed
        file_upload.state = "inbox"
        file_upload.decrypted_sha256 = unencrypted_checksum
        file_upload.encrypted_parts_md5 = encrypted_parts_md5
        file_upload.encrypted_parts_sha256 = encrypted_parts_sha256
        file_upload.inbox_upload_completed = True
        file_upload.state_updated = now_utc_ms_prec()
        s3_upload_details.completed = now_utc_ms_prec()
        await self._file_upload_dao.update(file_upload)
        await self._s3_upload_details_dao.update(s3_upload_details)

        # Update the FileUploadBox with new size and file count
        await self._update_box_stats(box_id=box_id, version=box_version)
        log.info("DB data updated for upload completion of file %s", file_id)

    async def remove_file_upload(self, *, box_id: UUID4, file_id: UUID4) -> None:
        """Remove a file upload and cancel the ongoing upload if applicable.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `BoxStateError` if the box exists but is locked.
        - `BoxVersionError` if the box version changed before stats could be updated.
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        # Make sure box exists and is unlocked (unless overridden)
        box = await self._get_unlocked_box(box_id=box_id)

        # Retrieve the FileUpload data
        try:
            file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError:
            log.info("File %s not found - presumed already deleted.", file_id)
            return

        # Retrieve the S3UploadDetails
        try:
            s3_upload_details = await self._s3_upload_details_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.S3UploadDetailsNotFoundError(file_id=file_id)
            log.error(error, extra={"box_id": box_id, "file_id": file_id})
            raise error from err

        # Remove the file from S3 using slightly different approach based on if finished
        if file_upload.inbox_upload_completed:
            await self._remove_completed_file_upload(
                s3_upload_details=s3_upload_details
            )
        else:
            await self._remove_incomplete_file_upload(
                s3_upload_details=s3_upload_details
            )
        await self._s3_upload_details_dao.delete(file_id)

        # Update the file_upload to 'cancelled'
        file_upload.state = "cancelled"
        file_upload.state_updated = now_utc_ms_prec()
        await self._file_upload_dao.update(file_upload)
        await self._update_box_stats(box_id=box_id, version=box.version)
        log.info("File %s deleted from box %s", file_id, box_id)

    async def _update_box_stats(self, *, box_id: UUID4, version: int) -> None:
        """Update FileUploadBox stats (file count & size) in an idempotent manner.

        Re-fetches the box to get the latest state, verifies the version is still
        current before applying any changes.

        This helps mitigate potential state inconsistency arising from a hard crash.

        Raises:
        - `BoxNotFoundError` if the box no longer exists.
        - `BoxVersionError` if the box version has changed since it was fetched.
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

        file_count = 0
        total_size = 0
        async for file_upload in self._file_upload_dao.find_all(
            mapping={"box_id": box_id, "state": {"$nin": ["cancelled", "failed"]}}
        ):
            file_count += 1
            total_size += file_upload.decrypted_size

        # Since every update triggers an event, only update if data differs
        if file_count != box.file_count or total_size != box.size:
            box.version += 1
            box.file_count = file_count
            box.size = total_size
            await self._file_upload_box_dao.update(box)

    async def create_file_upload_box(self, *, storage_alias: str) -> UUID4:
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
            storage_alias=storage_alias,
        )
        await self._file_upload_box_dao.insert(box)
        log.debug(
            "Inserted FileUploadBox %s", box.id, extra={"storage_alias": storage_alias}
        )
        return box.id

    async def lock_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Lock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `BoxVersionError` if the supplied version doesn't match the current version.
        - `IncompleteUploadsError` if the FileUploadBox has incomplete FileUploads.
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

        if box.state != "open":
            # This goes for archived boxes too
            log.info("Box with ID %s already locked.", box_id)
            return

        incomplete_files_cursor = self._file_upload_dao.find_all(
            mapping={"box_id": box_id, "inbox_upload_completed": False}
        )
        file_ids = sorted([x.id async for x in incomplete_files_cursor])
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
        try:
            box = await self._file_upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.BoxNotFoundError(box_id=box_id)
            log.error(error)
            raise error from err

        # Check version
        if box.version != version:
            error = self.BoxVersionError(box_id=box_id)
            log.error(error, extra={"box_id": box_id, "version": version})
            raise error

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
        file_ids = sorted([x.id async for x in files_not_interrogated_cursor])
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

        # Box exists, now get all completed file uploads
        file_uploads = [
            x
            async for x in self._file_upload_dao.find_all(
                mapping={"box_id": box_id, "inbox_upload_completed": True}
            )
        ]
        file_uploads.sort(key=lambda x: x.alias)
        return file_uploads

    async def process_interrogation_success(
        self, *, report: InterrogationSuccess
    ) -> None:
        """Update a FileUpload with the information from a corresponding successful
        interrogation report and remove it from the inbox bucket.

        Raises:
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
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
                    "Ignoring interrogation report for FileUpload %s since it is still"
                    + " in the 'init' state.",
                    file_id,
                )
                return
            case "inbox":
                # Update the FileUpload's parameters using the InterrogationReport
                file_upload.state = "interrogated"
                file_upload.state_updated = now_utc_ms_prec()
                file_upload.secret_id = report.secret_id
                file_upload.encrypted_parts_md5 = report.encrypted_parts_md5
                file_upload.encrypted_parts_sha256 = report.encrypted_parts_sha256
                file_upload.bucket_id = report.bucket_id
                file_upload.object_id = report.object_id
                file_upload.encrypted_size = report.encrypted_size
                log.debug("Marking FileUpload %s as '%s'", file_id, file_upload.state)
                await self._file_upload_dao.update(file_upload)
            case _:
                log.info(
                    "FileUpload %s was already marked as '%s', so it's likely"
                    + " this interrogation report has been processed already.",
                    file_id,
                    file_upload.state,
                )

        # Retrieve the S3UploadDetails
        try:
            s3_upload_details = await self._s3_upload_details_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.S3UploadDetailsNotFoundError(file_id=file_id)
            log.error(error, extra={"file_id": file_id})
            raise error from err

        await self._remove_completed_file_upload(s3_upload_details=s3_upload_details)

    async def process_interrogation_failure(
        self, *, report: InterrogationFailure
    ) -> None:
        """Update a FileUpload state to 'failed' and remove it from the inbox bucket.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
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

        # Retrieve the S3UploadDetails
        try:
            s3_upload_details = await self._s3_upload_details_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.S3UploadDetailsNotFoundError(file_id=file_id)
            log.error(error, extra={"file_id": file_id})
            raise error from err

        await self._remove_completed_file_upload(s3_upload_details=s3_upload_details)

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
