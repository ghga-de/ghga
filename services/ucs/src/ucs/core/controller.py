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
from typing import Any
from uuid import uuid4

from ghga_event_schemas.pydantic_ import (
    FileUpload,
    FileUploadBox,
    FileUploadReport,
    FileUploadState,
)
from ghga_service_commons.utils.multinode_storage import ObjectStorages
from hexkit.protocols.dao import ResourceAlreadyExistsError
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from ucs.config import Config
from ucs.core.models import S3UploadDetails
from ucs.ports.inbound.controller import UploadControllerPort
from ucs.ports.outbound.dao import (
    FileUploadBoxDao,
    FileUploadDao,
    ResourceNotFoundError,
    S3UploadDetailsDao,
)

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
        object_storages: ObjectStorages,
    ):
        self._config = config
        self._file_upload_box_dao = file_upload_box_dao
        self._file_upload_dao = file_upload_dao
        self._s3_upload_details_dao = s3_upload_details_dao
        self._object_storages = object_storages

    def _get_bucket_and_storage(
        self, storage_alias: str
    ) -> tuple[str, ObjectStorageProtocol]:
        """Return the bucket ID and ObjectStorageProtocol for a given storage alias.

        Raises `UnknownStorageAliasError` if the storage alias is not known.
        """
        try:
            bucket_id, object_storage = self._object_storages.for_alias(storage_alias)
        except KeyError as error:
            unknown_alias = self.UnknownStorageAliasError(storage_alias=storage_alias)
            log.error(unknown_alias, extra={"storage_alias": storage_alias})
            raise unknown_alias from error
        log.debug(
            "Found bucket '%s' and object storage for alias '%s'",
            bucket_id,
            storage_alias,
        )
        return bucket_id, object_storage

    async def _insert_file_upload_if_new(
        self, *, box: FileUploadBox, alias: str, size: int
    ) -> UUID4:
        """Create a new FileUpload for the provided file alias and return the file_id.

        This method tries to insert a new FileUpload with a random UUID4 for file_id.

        Raises `FileUploadAlreadyExists` if there's already a FileUpload for this alias
        and box_id.
        """
        box_id = box.id
        file_id = uuid4()

        try:
            file_upload = FileUpload(
                id=file_id,
                state=FileUploadState.INIT,
                box_id=box_id,
                alias=alias,
                size=size,
                checksum="",  # Checksum is empty until file upload is complete
            )

            await self._file_upload_dao.insert(file_upload)
            return file_id
        except ResourceAlreadyExistsError as err:
            error = self.FileUploadAlreadyExists(alias=alias)
            log.error(
                error,
                extra={
                    "box_id": box.id,
                    "generated_file_id": file_id,
                    "file_alias": alias,
                    "size": size,
                },
            )
            raise error from err

    async def _get_unlocked_box(self, *, box_id: UUID4) -> FileUploadBox:
        """Retrieve a FileUploadBox by ID.

        Raises:
        - `BoxNotFoundError` if the box does not exist
        - `LockedBoxError` if the box exists but is locked.
        """
        # Verify that the box exists
        try:
            box = await self._file_upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.BoxNotFoundError(box_id=box_id)
            log.error(error)
            raise error from err

        # Verify that the box is not locked
        if box.locked:
            error = self.LockedBoxError(box_id=box_id)
            log.error(error)
            raise error

        return box

    async def _remove_completed_file_upload(
        self, *, s3_upload_details: S3UploadDetails
    ) -> None:
        """Delete a completely uploaded file from S3 and blindly try to delete the
        associated multipart upload just to be sure.

        Does not delete any data from the DB.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
          If this occurs, developer intervention might be required.
        """
        object_id = str(s3_upload_details.file_id)
        storage_alias = s3_upload_details.storage_alias
        s3_upload_id = s3_upload_details.s3_upload_id
        bucket_id, object_storage = self._get_bucket_and_storage(
            storage_alias=storage_alias
        )

        if await object_storage.does_object_exist(
            bucket_id=bucket_id, object_id=object_id
        ):
            log.debug(
                "Attempting to delete file %s from bucket %s", object_id, bucket_id
            )
            await object_storage.delete_object(bucket_id=bucket_id, object_id=object_id)
            log.info("Deleted file %s from bucket %s", object_id, bucket_id)
        else:
            # Suppress the error in case this is a retry after, e.g. a network hiccup
            #  (wherein the upload was actually cancelled but user still saw an error)
            try:
                log.debug(
                    "Attempting to abort S3 upload %s if it still exists", s3_upload_id
                )
                await object_storage.abort_multipart_upload(
                    bucket_id=bucket_id,
                    object_id=object_id,
                    upload_id=s3_upload_id,
                )
            except object_storage.MultiPartUploadNotFoundError:
                log.info(
                    "No multipart upload found for ID %s. Presumed already aborted.",
                    s3_upload_id,
                )
            except object_storage.MultiPartUploadAbortError as err:
                file_id = s3_upload_details.file_id
                error = self.UploadAbortError(
                    file_id=file_id, s3_upload_id=s3_upload_id, bucket_id=bucket_id
                )
                log.error(
                    "Removed completely uploaded object from inbox, but also found"
                    + " an unexpected multipart upload. Received an error when upload"
                    + " abort was attempted. Please investigate.",
                    exc_info=True,
                    extra={
                        "s3_upload_id": s3_upload_id,
                        "file_id": file_id,
                        "object_id": object_id,
                        "bucket_id": bucket_id,
                        "storage_alias": storage_alias,
                    },
                )
                raise error from err

    async def _remove_incomplete_file_upload(
        self, *, s3_upload_details: S3UploadDetails
    ) -> None:
        """Abort an incomplete S3 multipart upload.

        Does not delete any data from the DB.

        Raises:
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        file_id = s3_upload_details.file_id
        storage_alias = s3_upload_details.storage_alias
        s3_upload_id = s3_upload_details.s3_upload_id
        bucket_id, object_storage = self._get_bucket_and_storage(
            storage_alias=storage_alias
        )

        try:
            log.debug(
                "Attempting to abort S3 upload %s since it should exist.", s3_upload_id
            )
            await object_storage.abort_multipart_upload(
                upload_id=s3_upload_id,
                bucket_id=bucket_id,
                object_id=str(file_id),
            )
            log.info("Successfully aborted S3 upload %s", s3_upload_id)
        except object_storage.MultiPartUploadAbortError as err:
            error = self.UploadAbortError(
                file_id=file_id, s3_upload_id=s3_upload_id, bucket_id=bucket_id
            )
            log.error(
                error,
                exc_info=True,
                extra={
                    "file_id": file_id,
                    "bucket_id": bucket_id,
                    "storage_alias": storage_alias,
                    "s3_upload_id": s3_upload_id,
                },
            )
            raise error from err
        except object_storage.MultiPartUploadNotFoundError:
            # This correspond to an inconsistency between the database and
            # the storage, however, since this cancel method might be used to
            # resolve this inconsistency, this exception will be ignored.
            pass

    async def initiate_file_upload(
        self, *, box_id: UUID4, alias: str, size: int
    ) -> UUID4:
        """Initialize a new multipart upload and return the file ID.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `LockedBoxError` if the box exists but is locked.
        - `FileUploadAlreadyExists` if there's already a FileUpload for this alias.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `OrphanedMultipartUploadError` if an S3 upload is already in progress.
        """
        extra: dict[str, Any] = {"box_id": box_id, "alias": alias}
        # Get the box and create the FileUpload
        box = await self._get_unlocked_box(box_id=box_id)

        # Get the S3 storage details
        storage_alias = box.storage_alias
        bucket_id, object_storage = self._get_bucket_and_storage(
            storage_alias=storage_alias
        )
        extra["storage_alias"] = storage_alias
        extra["bucked_id"] = bucket_id

        initiated = now_utc_ms_prec()  # Generate timestamp early to minimize error risk
        file_id = await self._insert_file_upload_if_new(box=box, alias=alias, size=size)
        log.info("FileUpload %s added for alias %s.", file_id, alias, extra=extra)

        # Initiate a new multipart file upload on the S3 instance
        try:
            s3_upload_id = await object_storage.init_multipart_upload(
                bucket_id=bucket_id, object_id=str(file_id)
            )
            log.debug(
                "S3 multipart upload %s created for file ID %s (file alias %s)",
                s3_upload_id,
                file_id,
                alias,
                extra=extra,
            )
        except object_storage.MultiPartUploadAlreadyExistsError as err:
            #  _insert_file_upload_if_new precludes the existence of a FileUpload
            #  with the same `file_id`. If there's no FileUpload with the same file_id,
            #  then there cannot be an upload for said file_id (in S3, file_id is object_id).
            #  The most likely cause for this situation is that a crash occurred between
            #  creating the S3 upload and inserting the S3UploadDetails. We can't assign
            #  S3 upload IDs, so if that data isn't saved to the DB, it is only preserved
            #  in the logs. There is no straightforward way to get the upload ID
            #  programmatically, so we can't auto-abort it, either. In this case a
            #  developer will have to manually intervene to cancel the upload. We will
            #  delete the FileUpload, however, so the user can immediately retry.
            error = self.OrphanedMultipartUploadError(
                file_id=file_id, bucket_id=bucket_id
            )
            log.critical(str(error), exc_info=True, extra=extra)
            await self._file_upload_dao.delete(file_id)
            log.debug("Cleanup performed - FileUpload %s deleted.", file_id)
            raise error from err

        # Insert S3UploadDetails. Don't check for duplicate because insert only
        #  occurs in this method and only if the FileUpload alias is new. The check for
        #  duplicates is performed in `_insert_validated_file_upload`.
        s3_upload = S3UploadDetails(
            file_id=file_id,
            storage_alias=storage_alias,
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
        return file_id

    async def get_part_upload_url(self, *, file_id: UUID4, part_no: int) -> str:
        """
        Create and return a pre-signed URL to upload the bytes for the file part with
        the given number of the upload with the given file ID.

        Raises:
        - `S3UploadDetailsNotFoundError` if no upload details are found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `S3UploadNotFoundError` if the S3 multipart upload can't be found.
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
        storage_alias = s3_upload_details.storage_alias
        s3_upload_id = s3_upload_details.s3_upload_id

        bucket_id, object_storage = self._get_bucket_and_storage(
            storage_alias=storage_alias
        )

        try:
            return await object_storage.get_part_upload_url(
                upload_id=s3_upload_id,
                bucket_id=bucket_id,
                object_id=str(file_id),
                part_number=part_no,
            )
        except object_storage.MultiPartUploadNotFoundError as err:
            error = self.S3UploadNotFoundError(
                s3_upload_id=s3_upload_id, bucket_id=bucket_id
            )
            log.error(
                error,
                exc_info=True,
                extra={
                    "s3_upload_id": s3_upload_id,
                    "bucket_id": bucket_id,
                    "file_id": file_id,
                    "part_no": part_no,
                    "storage_alias": storage_alias,
                },
            )
            raise error from err

    async def _compare_checksums(
        self,
        object_storage: ObjectStorageProtocol,
        bucket_id: str,
        file_id: UUID4,
        expected_checksum: str,
    ) -> None:
        """Compare checksums and raise a `ChecksumMismatchError` if they don't match."""
        actual_checksum = await object_storage.get_object_etag(
            bucket_id=bucket_id, object_id=str(file_id)
        )
        actual_checksum = actual_checksum.strip('"')

        if actual_checksum != expected_checksum:
            error = self.ChecksumMismatchError(file_id=file_id)
            extra = {
                "bucket_id": bucket_id,
                "file_id": file_id,
                "expected_checksum": expected_checksum,
                "actual_checksum": actual_checksum,
            }
            log.error(error, exc_info=True, extra=extra)
            raise error

    async def complete_file_upload(
        self,
        *,
        box_id: UUID4,
        file_id: UUID4,
        unencrypted_checksum: str,
        encrypted_checksum: str,
    ) -> None:
        """Instruct S3 to complete a multipart upload and compares the remote checksum
        with the value provided for `encrypted_checksum`. The `unencrypted_checksum`
        is stored in the database.

        Raises:
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
        - `BoxNotFoundError` if the FileUploadBox isn't found.
        - `LockedBoxError` if the box exists but is locked.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadCompletionError` if there's an error while telling S3 to complete the upload.
        - `ChecksumMismatchError` if the checksums don't match.
        """
        # Get the FileUploadBox instance and verify that it is unlocked
        box = await self._get_unlocked_box(box_id=box_id)
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
        storage_alias = s3_upload_details.storage_alias
        s3_upload_id = s3_upload_details.s3_upload_id

        # Complete the s3 multipart upload
        bucket_id, object_storage = self._get_bucket_and_storage(storage_alias)
        extra["storage_alias"] = storage_alias
        extra["s3_upload_id"] = s3_upload_id
        extra["bucket_id"] = bucket_id

        # Exit early if the FileUpload is complete (already in the inbox or archived)
        if file_upload.completed:
            log.info("FileUpload with ID %s already complete.", file_id)
            # If this method is called but the file is already completed, triple
            #  check that the box is up to date
            await self._update_box_stats(box=box)
            await self._compare_checksums(
                object_storage=object_storage,
                bucket_id=bucket_id,
                file_id=file_id,
                expected_checksum=encrypted_checksum,
            )
            return

        try:
            await object_storage.complete_multipart_upload(
                upload_id=s3_upload_id,
                bucket_id=bucket_id,
                object_id=str(file_id),
            )
            log.info(
                "S3 multipart upload %s completed for file %s",
                s3_upload_id,
                file_id,
                extra=extra,
            )
        except (
            object_storage.MultiPartUploadNotFoundError,
            object_storage.MultiPartUploadConfirmError,
        ) as err:
            # If the upload is not found, it's possible that it was already completed
            # and the UCS crashed before it was able to update its DB, so check that.
            if isinstance(
                err, object_storage.MultiPartUploadNotFoundError
            ) and await object_storage.does_object_exist(
                bucket_id=bucket_id, object_id=str(file_id)
            ):
                log.info(
                    "S3 multipart upload ID %s seems to have already been completed,"
                    + " since the expected object with ID %s exists. Proceeding to"
                    + " update DB.",
                    s3_upload_id,
                    file_id,
                    extra=extra,
                )
            else:
                # Object was not found or completion failed, so no recovery can be done.
                # User should request to delete the file and start over.
                error = self.UploadCompletionError(
                    file_id=file_id, s3_upload_id=s3_upload_id, bucket_id=bucket_id
                )
                log.error(error, exc_info=True, extra=extra)
                raise error from err

        await self._compare_checksums(
            object_storage=object_storage,
            bucket_id=bucket_id,
            file_id=file_id,
            expected_checksum=encrypted_checksum,
        )

        # Update local collections now that S3 upload is successfully completed
        file_upload.state = FileUploadState.INBOX
        file_upload.checksum = unencrypted_checksum
        file_upload.completed = True
        s3_upload_details.completed = now_utc_ms_prec()
        await self._file_upload_dao.update(file_upload)
        await self._s3_upload_details_dao.update(s3_upload_details)

        # Update the FileUploadBox with new size and file count
        await self._update_box_stats(box=box)
        log.debug("DB data updated for upload completion of file %s", file_id)

    async def remove_file_upload(self, *, box_id: UUID4, file_id: UUID4) -> None:
        """Remove a file upload and cancel the ongoing upload if applicable.

        Raises:
        - `BoxNotFoundError` if the box does not exist.
        - `LockedBoxError` if the box exists but is locked.
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

        try:
            s3_upload_details = await self._s3_upload_details_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.S3UploadDetailsNotFoundError(file_id=file_id)
            log.error(error, extra={"box_id": box_id, "file_id": file_id})
            raise error from err

        if file_upload.completed:
            await self._remove_completed_file_upload(
                s3_upload_details=s3_upload_details
            )
        else:
            await self._remove_incomplete_file_upload(
                s3_upload_details=s3_upload_details
            )
        await self._s3_upload_details_dao.delete(file_id)
        await self._file_upload_dao.delete(file_id)
        await self._update_box_stats(box=box)
        log.info("File %s deleted from box %s", file_id, box_id)

    async def _update_box_stats(self, *, box: FileUploadBox) -> None:
        """Update FileUploadBox stats (file count & size) in an idempotent manner.

        This helps mitigate potential state inconsistency arising from a hard crash.
        """
        file_count = 0
        total_size = 0
        async for file_upload in self._file_upload_dao.find_all(
            mapping={"box_id": box.id, "completed": True}
        ):
            file_count += 1
            total_size += file_upload.size

        # Since every update triggers an event, only update if data differs
        if file_count != box.file_count or total_size != box.size:
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

        box = FileUploadBox(id=uuid4(), storage_alias=storage_alias)
        await self._file_upload_box_dao.insert(box)
        log.debug(
            "Inserted FileUploadBox %s", box.id, extra={"storage_alias": storage_alias}
        )
        return box.id

    async def lock_file_upload_box(self, *, box_id: UUID4) -> None:
        """Lock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        - `IncompleteUploadsError` if the FileUploadBox has incomplete FileUploads.
        """
        try:
            box = await self._file_upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.BoxNotFoundError(box_id=box_id)
            log.error(error)
            raise error from err

        if box.locked:
            log.info("Box with ID %s already locked.", box_id)
            return

        incomplete_files_cursor = self._file_upload_dao.find_all(
            mapping={"box_id": box_id, "completed": False}
        )
        file_ids = sorted([x.id async for x in incomplete_files_cursor])
        if file_ids:
            error = self.IncompleteUploadsError(box_id=box_id, file_ids=file_ids)
            log.error(error, extra={"box_id": box_id, "file_ids": str(file_ids)})
            raise error

        box.locked = True
        await self._file_upload_box_dao.update(box)
        log.info("Locked box with ID %s.", box_id)

    async def unlock_file_upload_box(self, *, box_id: UUID4) -> None:
        """Unlock an existing FileUploadBox.

        Raises:
        - `BoxNotFoundError` if the FileUploadBox isn't found in the DB.
        """
        try:
            box = await self._file_upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.BoxNotFoundError(box_id=box_id)
            log.error(error)
            raise error from err

        if box.locked:
            box.locked = False
            await self._file_upload_box_dao.update(box)
            log.info("Unlocked box with ID %s", box_id)
        else:
            log.debug("Box with ID %s is already unlocked", box_id)

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
                mapping={"box_id": box_id, "completed": True}
            )
        ]
        file_uploads.sort(key=lambda x: x.alias)
        return file_uploads

    async def process_file_upload_report(
        self, *, file_upload_report: FileUploadReport
    ) -> None:
        """Use a file upload report to clean up a file from the inbox bucket and
        set the FileUpload state to 'archived'.

        Raises:
        - `S3UploadDetailsNotFoundError` if the S3UploadDetails aren't found.
        - `FileUploadNotFound` if the FileUpload isn't found.
        - `UnknownStorageAliasError` if the storage alias is not known.
        - `UploadAbortError` if there's an error instructing S3 to abort the upload.
        """
        file_id = file_upload_report.file_id
        try:
            file_upload = await self._file_upload_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.FileUploadNotFound(file_id=file_id)
            log.error(error, extra={"file_id": file_id})
            raise error from err

        match file_upload.state:
            case FileUploadState.INIT:
                log.warning(
                    "Ignoring FileUploadReport for FileUpload %s since it is still in the 'init' state.",
                    file_id,
                )
                return
            case FileUploadState.INBOX:
                file_upload.state = FileUploadState.ARCHIVED
                log.debug("Marking FileUpload %s as 'archived'", file_id)
                await self._file_upload_dao.update(file_upload)
            case FileUploadState.ARCHIVED:
                log.debug(
                    "FileUpload %s was already marked as 'archived', so it's likely"
                    + " this FileUploadReport has been processed already.",
                    file_id,
                )

        # Attempt to delete S3 file even if this event has been processed before
        try:
            s3_upload_details = await self._s3_upload_details_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            error = self.S3UploadDetailsNotFoundError(file_id=file_id)
            log.error(error, extra={"file_id": file_id})
            raise error from err

        await self._remove_completed_file_upload(s3_upload_details=s3_upload_details)
