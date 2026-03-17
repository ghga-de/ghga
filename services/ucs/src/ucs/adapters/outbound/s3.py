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

"""S3-based Implementation of object storage adapters."""

import logging

from ghga_service_commons.utils.multinode_storage import ObjectStorages
from hexkit.protocols.objstorage import ObjectStorageProtocol
from pydantic import UUID4

from ucs.config import Config
from ucs.core.models import FileUpload, S3UploadDetails
from ucs.ports.outbound.storage import S3ClientPort

log = logging.getLogger(__name__)


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

    async def init_multipart_upload(self, *, file_upload: FileUpload) -> str:
        """Initiate a new multipart upload for a FileUpload.

        Returns a str containing the multipart upload ID.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `OrphanedMultipartUploadError` if an S3 upload is already in progress.
        """
        bucket_id = file_upload.bucket_id
        object_id = file_upload.object_id
        _, object_storage = self._get_bucket_and_storage(file_upload.storage_alias)

        try:
            s3_upload_id = await object_storage.init_multipart_upload(
                bucket_id=bucket_id, object_id=str(object_id)
            )
            log.info(
                "S3 multipart upload %s created for file ID %s (file alias %s)",
                s3_upload_id,
                file_upload.id,
                file_upload.alias,
            )
            return s3_upload_id
        except object_storage.MultiPartUploadAlreadyExistsError as err:
            #  See the long note on UploadController.initiate_file_upload()
            raise self.OrphanedMultipartUploadError(
                file_id=file_upload.id, bucket_id=bucket_id
            ) from err

    async def get_part_upload_url(
        self, *, s3_upload_details: S3UploadDetails, part_no: int
    ) -> str:
        """Get a pre-signed URL to upload a specific part of a multipart upload.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadNotFoundError` if the multipart upload can't be found in S3.
        """
        _, object_storage = self._get_bucket_and_storage(
            s3_upload_details.storage_alias
        )
        try:
            return await object_storage.get_part_upload_url(
                upload_id=s3_upload_details.s3_upload_id,
                bucket_id=s3_upload_details.bucket_id,
                object_id=str(s3_upload_details.object_id),
                part_number=part_no,
            )
        except object_storage.MultiPartUploadNotFoundError as err:
            error = self.S3UploadNotFoundError(
                s3_upload_id=s3_upload_details.s3_upload_id,
                bucket_id=s3_upload_details.bucket_id,
            )
            log.error(
                error,
                exc_info=True,
                extra={
                    "s3_upload_id": s3_upload_details.s3_upload_id,
                    "bucket_id": s3_upload_details.bucket_id,
                    "file_id": s3_upload_details.file_id,
                    "storage_alias": s3_upload_details.storage_alias,
                },
            )
            raise error from err

    async def complete_multipart_upload(
        self, *, s3_upload_details: S3UploadDetails
    ) -> None:
        """Instruct S3 to assemble all uploaded parts into the final object.

        Recovers idempotently if the upload was already completed (object exists).

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadCompletionError` if the upload cannot be completed or found.
        """
        bucket_id = s3_upload_details.bucket_id
        object_id = str(s3_upload_details.object_id)
        s3_upload_id = s3_upload_details.s3_upload_id
        file_id = s3_upload_details.file_id
        _, object_storage = self._get_bucket_and_storage(
            s3_upload_details.storage_alias
        )

        try:
            await object_storage.complete_multipart_upload(
                upload_id=s3_upload_id,
                bucket_id=bucket_id,
                object_id=object_id,
            )
            log.info(
                "S3 multipart upload %s completed for file %s", s3_upload_id, file_id
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
                    s3_upload_details.object_id,
                )
            else:
                error = self.S3UploadCompletionError(
                    file_id=file_id, s3_upload_id=s3_upload_id, bucket_id=bucket_id
                )
                log.error(
                    error,
                    exc_info=True,
                    extra={
                        "s3_upload_id": s3_upload_id,
                        "bucket_id": bucket_id,
                        "file_id": file_id,
                        "storage_alias": s3_upload_details.storage_alias,
                    },
                )
                raise error from err

    async def get_object_etag(
        self, *, s3_upload_details: S3UploadDetails, object_id: UUID4
    ) -> str:
        """Return the ETag of an object in the inbox bucket (quotes stripped).

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
        """
        _, object_storage = self._get_bucket_and_storage(
            s3_upload_details.storage_alias
        )
        etag = await object_storage.get_object_etag(
            bucket_id=s3_upload_details.bucket_id, object_id=str(object_id)
        )
        return etag.strip('"')

    async def delete_inbox_file(self, *, s3_upload_details: S3UploadDetails) -> None:
        """Delete a fully uploaded file from the inbox, or abort any stale multipart.

        If the object exists it is deleted. If only an in-progress multipart upload
        exists, that is aborted instead. A missing multipart upload is tolerated.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadAbortError` if an abort is required but fails.
        """
        object_id = str(s3_upload_details.object_id)
        s3_upload_id = s3_upload_details.s3_upload_id
        bucket_id = s3_upload_details.bucket_id
        file_id = s3_upload_details.file_id
        _, object_storage = self._get_bucket_and_storage(
            s3_upload_details.storage_alias
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
                error = self.S3UploadAbortError(
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
                        "storage_alias": s3_upload_details.storage_alias,
                    },
                )
                raise error from err

    async def abort_multipart_upload(
        self, *, s3_upload_details: S3UploadDetails
    ) -> None:
        """Abort an in-progress multipart upload. Tolerates a missing upload.

        Raises:
            `UnknownStorageAliasError` if the storage alias is not known.
            `S3UploadAbortError` if the abort fails.
        """
        file_id = s3_upload_details.file_id
        s3_upload_id = s3_upload_details.s3_upload_id
        bucket_id = s3_upload_details.bucket_id
        _, object_storage = self._get_bucket_and_storage(
            s3_upload_details.storage_alias
        )

        try:
            log.debug(
                "Attempting to abort S3 upload %s since it should exist.", s3_upload_id
            )
            await object_storage.abort_multipart_upload(
                upload_id=s3_upload_id,
                bucket_id=bucket_id,
                object_id=str(s3_upload_details.object_id),
            )
            log.info("Successfully aborted S3 upload %s", s3_upload_id)
        except object_storage.MultiPartUploadAbortError as err:
            error = self.S3UploadAbortError(
                file_id=file_id, s3_upload_id=s3_upload_id, bucket_id=bucket_id
            )
            log.error(
                error,
                exc_info=True,
                extra={
                    "file_id": file_id,
                    "bucket_id": bucket_id,
                    "storage_alias": s3_upload_details.storage_alias,
                    "s3_upload_id": s3_upload_id,
                },
            )
            raise error from err
        except object_storage.MultiPartUploadNotFoundError:
            # This corresponds to an inconsistency between the database and
            # the storage, however, since this cancel method might be used to
            # resolve this inconsistency, this exception will be ignored.
            pass
