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

"""S3-based Implementation of object storage adapters."""

import logging
from contextlib import contextmanager
from typing import Any

from ghga_service_commons.utils.multinode_storage import ObjectStorages
from hexkit.protocols.objstorage import ObjectStorageProtocol
from pydantic import UUID4

from ucs.config import Config
from ucs.core.models import FileUpload, FileUploadBasics
from ucs.ports.outbound.storage import S3ClientPort

log = logging.getLogger(__name__)


@contextmanager
def handle_bucket_and_general_s3_errors(
    *, op_name: str, bucket_id: str, extra: dict[str, Any]
):
    """Consolidate the uniform logic for BucketNotFound and catch-all S3 errors.

    Any error handling performed within the yield takes priority.
    """
    try:
        yield
    except ObjectStorageProtocol.BucketNotFoundError as err:
        error = S3ClientPort.BucketNotFoundError(bucket_id=bucket_id)
        log.error(error, extra=extra)
        raise error from err
    except ObjectStorageProtocol.ObjectStorageProtocolError as err:
        error = S3ClientPort.S3OperationError(operation=op_name, details=str(err))
        log.error(error, exc_info=True, extra=extra)
        raise error from err


class S3Client(S3ClientPort):
    """A class that isolates S3 logic and error handling from the core"""

    def __init__(self, *, config: Config, object_storages: ObjectStorages):
        self._config = config
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

    def get_bucket_id_for_alias(self, *, storage_alias: str) -> str:
        """Retrieve the bucket ID for a given storage alias.

        Raises `UnknownStorageAliasError` if the storage alias is not known.
        """
        bucket_id, _ = self._get_bucket_and_storage(storage_alias)
        return bucket_id

    async def init_multipart_upload(
        self, *, file_upload_basics: FileUploadBasics
    ) -> str:
        """Initiate a new multipart upload for a FileUpload.

        Returns a str containing the multipart upload ID.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `OrphanedMultipartUploadError` if an S3 upload is already in progress.
            `BucketNotFoundError` if the configured bucket does not exist in S3.
            `S3OperationError` if S3 returns any other unexpected error.
        """
        bucket_id = file_upload_basics.bucket_id
        object_id = file_upload_basics.object_id
        _, object_storage = self._get_bucket_and_storage(
            file_upload_basics.storage_alias
        )
        extra = {
            "bucket_id": bucket_id,
            "file_id": file_upload_basics.id,
            "storage_alias": file_upload_basics.storage_alias,
        }

        with handle_bucket_and_general_s3_errors(
            op_name="init_multipart_upload", bucket_id=bucket_id, extra=extra
        ):
            try:
                s3_upload_id = await object_storage.init_multipart_upload(
                    bucket_id=bucket_id, object_id=str(object_id)
                )
                log.info(
                    "S3 multipart upload %s created for file ID %s (file alias %s)",
                    s3_upload_id,
                    file_upload_basics.id,
                    file_upload_basics.alias,
                )
                return s3_upload_id
            except (
                object_storage.MultiPartUploadAlreadyExistsError,
                object_storage.MultipleActiveUploadsError,
            ) as err:
                #  See the long note on UploadController.initiate_file_upload()
                raise self.OrphanedMultipartUploadError(
                    file_id=file_upload_basics.id, bucket_id=bucket_id
                ) from err

    async def get_part_upload_url(
        self, *, file_upload: FileUpload, part_no: int
    ) -> str:
        """Get a pre-signed URL to upload a specific part of a multipart upload.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadNotFoundError` if the multipart upload can't be found in S3.
            `BucketNotFoundError` if the configured bucket does not exist in S3.
            `S3OperationError` if S3 returns any other unexpected error.
        """
        _, object_storage = self._get_bucket_and_storage(file_upload.storage_alias)
        extra = {
            "s3_upload_id": file_upload.s3_upload_id,
            "bucket_id": file_upload.bucket_id,
            "file_id": file_upload.id,
            "storage_alias": file_upload.storage_alias,
        }

        with handle_bucket_and_general_s3_errors(
            op_name="get_part_upload_url", bucket_id=file_upload.bucket_id, extra=extra
        ):
            try:
                return await object_storage.get_part_upload_url(
                    upload_id=file_upload.s3_upload_id,
                    bucket_id=file_upload.bucket_id,
                    object_id=str(file_upload.object_id),
                    part_number=part_no,
                )
            except object_storage.MultiPartUploadNotFoundError as err:
                error = self.S3UploadNotFoundError(
                    s3_upload_id=file_upload.s3_upload_id,
                    bucket_id=file_upload.bucket_id,
                )
                log.error(error, extra=extra)
                raise error from err

    async def complete_multipart_upload(self, *, file_upload: FileUpload) -> None:
        """Instruct S3 to assemble all uploaded parts into the final object.

        Recovers idempotently if the upload was already completed (object exists).

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadCompletionError` if the upload cannot be completed or found.
            `BucketNotFoundError` if the configured bucket does not exist in S3.
            `S3OperationError` if S3 returns any other unexpected error.
        """
        bucket_id = file_upload.bucket_id
        object_id = str(file_upload.object_id)
        s3_upload_id = file_upload.s3_upload_id
        file_id = file_upload.id
        _, object_storage = self._get_bucket_and_storage(file_upload.storage_alias)
        extra = {
            "s3_upload_id": s3_upload_id,
            "bucket_id": bucket_id,
            "file_id": file_id,
            "storage_alias": file_upload.storage_alias,
        }

        with handle_bucket_and_general_s3_errors(
            op_name="complete_multipart_upload",
            bucket_id=file_upload.bucket_id,
            extra=extra,
        ):
            try:
                await object_storage.complete_multipart_upload(
                    upload_id=s3_upload_id,
                    bucket_id=bucket_id,
                    object_id=object_id,
                )
                log.info(
                    "S3 multipart upload %s completed for file %s",
                    s3_upload_id,
                    file_id,
                )
            except (
                object_storage.MultiPartUploadNotFoundError,
                object_storage.MultiPartUploadConfirmError,
            ) as err:
                if isinstance(
                    err, object_storage.MultiPartUploadNotFoundError
                ) and await object_storage.does_object_exist(
                    bucket_id=bucket_id, object_id=object_id
                ):
                    log.info(
                        "S3 multipart upload ID %s seems to have already been completed,"
                        + " since the expected object with ID %s exists. Proceeding to"
                        + " update DB.",
                        s3_upload_id,
                        file_upload.object_id,
                    )
                else:
                    error = self.S3UploadCompletionError(
                        file_id=file_id, s3_upload_id=s3_upload_id, bucket_id=bucket_id
                    )
                    log.error(error, exc_info=True, extra=extra)
                    raise error from err

    async def get_object_etag(
        self, *, file_upload: FileUpload, object_id: UUID4
    ) -> str:
        """Return the ETag of an object in the inbox bucket (quotes stripped).

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `BucketNotFoundError` if the configured bucket does not exist in S3.
            `S3ObjectNotFoundError` if the object is not found in S3.
            `S3OperationError` if S3 returns any other unexpected error.
        """
        _, object_storage = self._get_bucket_and_storage(file_upload.storage_alias)
        bucket_id = file_upload.bucket_id
        extra = {
            "bucket_id": bucket_id,
            "object_id": str(object_id),
            "file_id": file_upload.id,
            "storage_alias": file_upload.storage_alias,
        }

        with handle_bucket_and_general_s3_errors(
            op_name="get_object_etag", bucket_id=file_upload.bucket_id, extra=extra
        ):
            try:
                etag = await object_storage.get_object_etag(
                    bucket_id=bucket_id, object_id=str(object_id)
                )
            except object_storage.ObjectNotFoundError as err:
                error = self.S3ObjectNotFoundError(
                    bucket_id=bucket_id, object_id=str(object_id)
                )
                log.error(error, extra=extra)
                raise error from err
            except object_storage.BucketNotFoundError as err:
                error = self.BucketNotFoundError(bucket_id=bucket_id)
                log.error(error, extra=extra)
                raise error from err
            except object_storage.ObjectStorageProtocolError as err:
                error = self.S3OperationError(
                    operation="get_object_etag", details=str(err)
                )
                log.error(error, exc_info=True, extra=extra)
                raise error from err
            return etag.strip('"')

    async def delete_inbox_file(self, *, file_upload: FileUpload) -> None:
        """Delete a fully uploaded file from the inbox, or abort any stale multipart.

        If the object exists it is deleted. If only an in-progress multipart upload
        exists, that is aborted instead. A missing multipart upload is tolerated.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadAbortError` if an abort is required but fails.
            `BucketNotFoundError` if the configured bucket does not exist in S3.
            `S3OperationError` if S3 returns any other unexpected error.
        """
        object_id = str(file_upload.object_id)
        s3_upload_id = file_upload.s3_upload_id
        bucket_id = file_upload.bucket_id
        file_id = file_upload.id
        _, object_storage = self._get_bucket_and_storage(file_upload.storage_alias)
        extra = {
            "s3_upload_id": s3_upload_id,
            "file_id": file_id,
            "object_id": object_id,
            "bucket_id": bucket_id,
            "storage_alias": file_upload.storage_alias,
        }

        with handle_bucket_and_general_s3_errors(
            op_name="does_object_exist", bucket_id=file_upload.bucket_id, extra=extra
        ):
            does_object_exist = await object_storage.does_object_exist(
                bucket_id=bucket_id, object_id=object_id
            )
            if does_object_exist:
                await object_storage.delete_object(
                    bucket_id=bucket_id, object_id=object_id
                )
                log.info("Deleted object %s from bucket %s.", object_id, bucket_id)
                return
            else:
                log.info(
                    "No object found with ID %s. It might be deleted already, or maybe"
                    + " the upload wasn't completed. Will attempt to abort upload %s.",
                    object_id,
                    s3_upload_id,
                )

        with handle_bucket_and_general_s3_errors(
            op_name="abort_multipart_upload",
            bucket_id=file_upload.bucket_id,
            extra=extra,
        ):
            # Suppress the error in case this is a retry after, e.g. a network
            #  hiccup (wherein the upload was actually cancelled but user still
            #  saw an error)
            try:
                log.debug(
                    "Attempting to abort S3 upload %s if it still exists",
                    s3_upload_id,
                )
                await object_storage.abort_multipart_upload(
                    bucket_id=bucket_id,
                    object_id=object_id,
                    upload_id=s3_upload_id,
                )
            except object_storage.MultiPartUploadNotFoundError:
                log.info(
                    "No multipart upload found for ID %s."
                    + " Presumed already aborted.",
                    s3_upload_id,
                )
            except object_storage.MultiPartUploadAbortError as err:
                error = self.S3UploadAbortError(
                    file_id=file_id,
                    s3_upload_id=s3_upload_id,
                    bucket_id=bucket_id,
                    object_id=object_id,
                )
                log.error(
                    "Removed completely uploaded object from inbox, but also"
                    + " found an unexpected multipart upload. Received an error"
                    + " when upload abort was attempted. Please investigate.",
                    exc_info=True,
                    extra=extra,
                )
                raise error from err

    async def get_object_size(
        self, *, file_upload: FileUpload, object_id: UUID4
    ) -> int:
        """Return the size in bytes of an object in the inbox bucket.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `BucketNotFoundError` if the configured bucket does not exist in S3.
            `S3ObjectNotFoundError` if the object is not found in S3.
            `S3OperationError` if S3 returns any other unexpected error.
        """
        bucket_id = file_upload.bucket_id
        _, object_storage = self._get_bucket_and_storage(file_upload.storage_alias)
        extra = {
            "bucket_id": bucket_id,
            "object_id": str(object_id),
            "file_id": file_upload.id,
            "storage_alias": file_upload.storage_alias,
        }

        with handle_bucket_and_general_s3_errors(
            op_name="get_object_size", bucket_id=file_upload.bucket_id, extra=extra
        ):
            try:
                return await object_storage.get_object_size(
                    bucket_id=bucket_id, object_id=str(object_id)
                )
            except object_storage.ObjectNotFoundError as err:
                error = self.S3ObjectNotFoundError(
                    bucket_id=bucket_id, object_id=str(object_id)
                )
                log.error(error, extra=extra)
                raise error from err

    async def abort_multipart_upload(
        self,
        *,
        storage_alias: str,
        object_id: str,
        s3_upload_id: str,
        file_id: UUID4 | None = None,
    ) -> None:
        """Abort an in-progress multipart upload. Tolerates a missing upload.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadAbortError` if the abort fails.
            `BucketNotFoundError` if the configured bucket does not exist in S3.
            `S3OperationError` if S3 returns any other unexpected error.
        """
        bucket_id, object_storage = self._get_bucket_and_storage(storage_alias)
        extra = {
            "file_id": file_id,
            "bucket_id": bucket_id,
            "storage_alias": storage_alias,
            "s3_upload_id": s3_upload_id,
        }

        with handle_bucket_and_general_s3_errors(
            op_name="abort_multipart_upload", bucket_id=bucket_id, extra=extra
        ):
            try:
                log.debug(
                    "Attempting to abort S3 upload %s (object %s).",
                    s3_upload_id,
                    object_id,
                )
                await object_storage.abort_multipart_upload(
                    upload_id=s3_upload_id,
                    bucket_id=bucket_id,
                    object_id=object_id,
                )
                log.info(
                    "Aborted S3 multipart upload %s (object %s).",
                    s3_upload_id,
                    object_id,
                )
            except object_storage.MultiPartUploadNotFoundError:
                log.info(
                    "No multipart upload found with the ID %s. Presumed already aborted.",
                    s3_upload_id,
                )
            except object_storage.MultiPartUploadAbortError as err:
                error = self.S3UploadAbortError(
                    s3_upload_id=s3_upload_id,
                    object_id=object_id,
                    bucket_id=bucket_id,
                    file_id=file_id,
                )
                log.error(
                    error,
                    exc_info=True,
                    extra={
                        "s3_upload_id": s3_upload_id,
                        "object_id": object_id,
                        "bucket_id": bucket_id,
                        "storage_alias": storage_alias,
                        "file_id": file_id,
                    },
                )
                raise error from err

    async def list_all_multipart_uploads(self, *, storage_alias: str) -> dict[str, str]:
        """Returns all active multipart uploads for the bucket associated with the alias.

        Returns a dict of s3_upload_id -> object_id.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
        """
        bucket_id, object_storage = self._get_bucket_and_storage(storage_alias)
        extra = {"storage_alias": storage_alias, "bucket_id": bucket_id}
        with handle_bucket_and_general_s3_errors(
            op_name="get_all_multipart_uploads", bucket_id=bucket_id, extra=extra
        ):
            return await object_storage.get_all_multipart_uploads(bucket_id=bucket_id)

    async def cleanup_orphaned_objects(
        self, *, storage_alias: str, known_object_ids: set[str]
    ):
        """Clean out all orphaned object IDs in the inbox bucket.

        When finished, log basic stats for deleted objects.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `BucketNotFoundError` if the configured bucket does not exist in S3.
        """
        bucket_id, object_storage = self._get_bucket_and_storage(storage_alias)
        extra: dict[str, Any] = {"storage_alias": storage_alias, "bucket_id": bucket_id}
        try:
            object_ids = await object_storage.list_all_object_ids(bucket_id=bucket_id)
        except ObjectStorageProtocol.BucketNotFoundError as err:
            error = S3ClientPort.BucketNotFoundError(bucket_id=bucket_id)
            log.error(error, extra=extra)
            raise error from err

        orphaned_object_ids = set(object_ids) - known_object_ids

        # Return early if no orphaned objects
        if not orphaned_object_ids:
            log.info("Did not detect any orphaned objects in the bucket %s.", bucket_id)

        deleted_ids = []
        missing_ids = []
        problem_ids = []
        for object_id in orphaned_object_ids:
            try:
                await object_storage.delete_object(
                    bucket_id=bucket_id, object_id=object_id
                )
            except ObjectStorageProtocol.ObjectNotFoundError:
                missing_ids.append(object_id)
            except ObjectStorageProtocol.ObjectStorageProtocolError as err:
                log.error(
                    "Unable to clean up object %s from bucket %s in storage alias %s"
                    + " because of the following error: %s",
                    object_id,
                    bucket_id,
                    storage_alias,
                    str(err),
                    extra={**extra, "object_id": object_id},
                )
                problem_ids.append(object_id)
            else:
                deleted_ids.append(object_id)

        problem_msg = ""
        if problem_ids or missing_ids:
            problem_msg = (
                f" An additional {len(problem_ids)} object(s) could not be deleted and"
                + f" {len(missing_ids)} object(s) were no longer present by the time"
                + " deletion was attempted."
            )
            extra["could_not_delete_count"] = len(problem_ids)
            extra["could_not_delete_object_ids"] = problem_ids
            extra["no_longer_present_count"] = len(missing_ids)
            extra["no_longer_present_object_ids"] = missing_ids

        extra["deleted_count"] = len(deleted_ids)
        extra["deleted_object_ids"] = deleted_ids
        log.info(
            "Cleaned up %i orphaned object(s) from bucket %s in storage alias %s.%s",
            len(deleted_ids),
            bucket_id,
            storage_alias,
            problem_msg,
            extra=extra,
        )
