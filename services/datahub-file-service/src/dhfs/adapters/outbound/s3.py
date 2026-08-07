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

"""Outbound adapter that interacts directly with S3 object storage"""

import base64
import logging

import httpx
from async_lru import alru_cache
from tenacity import RetryError

from dhfs.adapters.outbound.http import check_for_request_errors
from dhfs.config import Config
from dhfs.constants import (
    DOWNLOAD_URL_CACHE_TIME,
    DOWNLOAD_URL_LIFESPAN,
    URL_CACHE_SIZE,
)
from dhfs.core.models import FileUpload
from dhfs.ports.outbound.s3 import S3ClientPort
from hexkit.protocols.objstorage import ObjectStorageProtocol

log = logging.getLogger(__name__)

__all__ = ["S3Client"]


class S3Client(S3ClientPort):
    """Performs S3 upload/download operations with error handling"""

    def __init__(
        self,
        *,
        config: Config,
        object_storage: ObjectStorageProtocol,
        httpx_client: httpx.AsyncClient,
    ) -> None:
        self._config = config
        self._storage = object_storage
        self._interrogation_bucket_id = config.interrogation_bucket_id
        self._httpx_client = httpx_client

    async def get_is_file_in_inbox(self, *, file: FileUpload) -> bool:
        """Return a bool indicating whether the file exists in the inbox.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        """
        extra = {"inbox_object_id": file.object_id, "inbox_bucket_id": file.bucket_id}
        log.debug(
            "File %s: Verifying that the object exists in the '%s' bucket.",
            file.id,
            file.bucket_id,
            extra=extra,
        )
        try:
            exists = await self._storage.does_object_exist(
                bucket_id=file.bucket_id, object_id=str(file.object_id)
            )
        except ObjectStorageProtocol.BucketNotFoundError as err:
            raise self.BucketNotFoundError(
                bucket_id=self._interrogation_bucket_id
            ) from err
        if exists:
            log.debug(
                "File %s: Confirmed that the object exists in the '%s' bucket.",
                file.id,
                file.bucket_id,
                extra=extra,
            )
        else:
            log.warning(
                "File %s: The object was not found in the '%s' bucket.",
                file.id,
                file.bucket_id,
                extra=extra,
            )
        return exists

    async def list_files_in_interrogation_bucket(self) -> list[str]:
        """Returns a list of object IDs from the interrogation bucket.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        """
        try:
            object_ids = await self._storage.list_all_object_ids(
                bucket_id=self._interrogation_bucket_id
            )
            log.debug(
                "Retrieved list of %i object ID(s) from the '%s' bucket.",
                len(object_ids),
                self._interrogation_bucket_id,
            )
            return sorted(object_ids)
        except ObjectStorageProtocol.BucketNotFoundError as err:
            raise self.BucketNotFoundError(
                bucket_id=self._interrogation_bucket_id
            ) from err

    @alru_cache(maxsize=URL_CACHE_SIZE, typed=True, ttl=DOWNLOAD_URL_CACHE_TIME)
    async def _get_download_url(self, *, bucket_id: str, object_id: str) -> str:
        """Generate a download URL for an object in the inbox bucket.

        Relies on cache to prevent excessive outbound calls.

        Raises:
        - BucketNotFoundError if the inbox bucket doesn't exist.
        - ObjectNotFoundError if the file doesn't exist in the inbox.
        """
        try:
            return await self._storage.get_object_download_url(
                bucket_id=bucket_id,
                object_id=object_id,
                expires_after=DOWNLOAD_URL_LIFESPAN,
            )
        except ObjectStorageProtocol.BucketNotFoundError as err:
            raise self.BucketNotFoundError(bucket_id=bucket_id) from err
        except ObjectStorageProtocol.ObjectNotFoundError as err:
            raise self.ObjectNotFoundError(object_id=object_id) from err
        except Exception as err:
            raise self.S3OperationError(
                "An unexpected error occurred while trying to generate a download URL"
                + f" for object {object_id} in bucket {bucket_id}."
            ) from err

    async def fetch_file_content_range(
        self,
        *,
        bucket_id: str,
        object_id: str,
        start: int,
        stop: int,
        bust_cache: bool = False,
    ) -> bytes:
        """Download a single file part for the bytes in range `start` - `stop` (exclusive end, like Python slicing).

        `bust_cache` will refresh the download url used for the object.

        Raises:
        - BucketNotFoundError if the inbox bucket doesn't exist.
        - ObjectNotFoundError if the file doesn't exist in the inbox.
        - DownloadError if the download request fails or returns an unexpected status code.
        """
        if bust_cache:
            self._get_download_url.cache_invalidate(
                bucket_id=bucket_id, object_id=object_id
            )

        download_url = await self._get_download_url(
            bucket_id=bucket_id, object_id=object_id
        )

        headers = httpx.Headers(
            {
                "Range": f"bytes={start}-{stop - 1}",  # HTTP Range is inclusive, so subtract 1
                "Cache-Control": "no-store",  # don't cache part downloads
            }
        )
        try:
            response = await self._httpx_client.get(download_url, headers=headers)
        except RetryError as retry_error:
            check_for_request_errors(retry_error, download_url)
            response = retry_error.last_attempt.result()

        status_code = response.status_code
        if status_code in (200, 206):
            return response.content

        if status_code == 403 and not bust_cache:
            log.debug(
                "Object %s: Download URL is stale - generating a fresh one.", object_id
            )
            return await self.fetch_file_content_range(
                bucket_id=bucket_id,
                object_id=object_id,
                start=start,
                stop=stop,
                bust_cache=True,
            )

        error = self.DownloadError(
            bucket_id=bucket_id, object_id=object_id, status_code=status_code
        )
        # This particular error is logged as the response could be useful for debugging
        log.debug(
            error,
            extra={
                "response_detail": response.content.decode("ascii", errors="ignore")
            },
        )
        raise error

    async def init_interrogation_bucket_upload(self, *, object_id: str) -> str:
        """Start a multipart upload to the interrogation bucket.

        If the object already exists in the interrogation bucket for any reason, it will
        be deleted and the interrogation process proceeds as if the object had never
        been there.

        Raises:
        - UploadInitError if an ongoing upload already exists for the object or if an unexpected error occurs.
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        """
        object_exists = await self._storage.does_object_exist(
            bucket_id=self._interrogation_bucket_id, object_id=object_id
        )

        if object_exists:
            # Delete and start the process over again
            log.info(
                "Object %s: An object with the same ID already exists in interrogation"
                + " bucket -- deleting before beginning interrogation.",
                object_id,
            )
            await self._storage.delete_object(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            )

        try:
            return await self._storage.init_multipart_upload(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            )
        except ObjectStorageProtocol.MultiPartUploadAlreadyExistsError as err:
            raise self.UploadInitError(object_id=object_id) from err
        except ObjectStorageProtocol.BucketNotFoundError as err:
            bucket_error = self.BucketNotFoundError(
                bucket_id=self._interrogation_bucket_id
            )
            raise bucket_error from err

    async def _get_part_upload_url(
        self,
        *,
        upload_id: str,
        object_id: str,
        part_no: int,
        md5_base64: str,
    ) -> str:
        """Retrieve a presigned part upload URL for a given file part"""
        # Convert MD5 to base64 for S3
        try:
            return await self._storage.get_part_upload_url(
                upload_id=upload_id,
                bucket_id=self._interrogation_bucket_id,
                object_id=object_id,
                part_number=part_no,
                part_md5=md5_base64,
            )
        except ObjectStorageProtocol.BucketNotFoundError as err:
            bucket_error = self.BucketNotFoundError(
                bucket_id=self._interrogation_bucket_id
            )
            raise bucket_error from err
        except ObjectStorageProtocol.MultiPartUploadNotFoundError as err:
            raise self.UploadURLMissingUploadError(upload_id=upload_id) from err

    async def upload_file_part(
        self,
        *,
        upload_id: str,
        object_id: str,
        part_no: int,
        part_md5: bytes,
        part: bytes,
    ) -> None:
        """Upload a single re-encrypted file part.

        Raises:
        - BadPartMD5Error if the specified MD5 doesn't match the MD5 calculated by S3.
        - BucketNotFoundError if the interrogation bucket is missing.
        - UploadPartError if any other error causes the part upload to fail.
        """
        md5_base64 = base64.b64encode(part_md5).decode()
        upload_url = await self._get_part_upload_url(
            upload_id=upload_id,
            object_id=object_id,
            part_no=part_no,
            md5_base64=md5_base64,
        )

        try:
            log.debug("Object %s: Uploading part number %i.", object_id, part_no)
            response = await self._httpx_client.put(
                upload_url, content=part, headers={"Content-MD5": md5_base64}
            )
        except RetryError as retry_error:
            check_for_request_errors(retry_error, upload_url)
            response = retry_error.last_attempt.result()

        if response.status_code != 200:
            status_code = response.status_code

            if status_code == 400:
                # A bad MD5 means that uploading the re-encrypted file has failed
                raise self.BadPartMD5Error(part_no=part_no, object_id=object_id)
            detail = response.content.decode()
            raise self.UploadPartError(
                object_id=object_id,
                part_no=part_no,
                status_code=response.status_code,
                detail=detail,
            )

    async def complete_upload(
        self, *, upload_id: str, object_id: str, part_count: int
    ) -> str:
        """Complete a multipart upload for an object in the interrogation bucket.

        Returns the object's ETag (which is the MD5 checksum of the encrypted file).

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        - IntegrityError if the number of uploaded parts doesn't match the expected count.
        - UploadCompletionError if the upload doesn't exist or another error prevents completion.
        """
        try:
            # Complete the upload
            await self._storage.complete_multipart_upload(
                upload_id=upload_id,
                bucket_id=self._interrogation_bucket_id,
                object_id=object_id,
                anticipated_part_quantity=part_count,
            )

            # We need to compare S3 ETag with locally calculated MD5, so fetch the etag
            etag = await self._storage.get_object_etag(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            )

            return etag.strip('"')
        except ObjectStorageProtocol.BucketNotFoundError as err:
            # At the completion stage, this shouldn't happen. Initiating and concluding
            #  the MPU have to occur in the same service instance lifetime, so bad
            #  bucket config should have been caught when starting interrogation.
            # We have no choice here but to perform cleanup and raise an error.
            bucket_error = self.BucketNotFoundError(
                bucket_id=self._interrogation_bucket_id
            )
            raise bucket_error from err
        except ObjectStorageProtocol.MultiPartUploadConfirmError as err:
            # In this case, the Interrogator needs to know that the upload has failed
            #  but the S3 client can proactively perform cleanup.
            raise self.IntegrityError(upload_id=upload_id, object_id=object_id) from err
        except ObjectStorageProtocol.MultiPartUploadNotFoundError as err:
            # This isn't as critical as the BucketNotFoundError as it's not a config issue.
            if not await self._storage.does_object_exist(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            ):
                raise self.UploadCompletionError(
                    upload_id=upload_id, object_id=object_id
                ) from err
            # If the object exists, then the UploadNotFoundError must have occurred
            #  due to some timing hiccup -- the file is there so we can squash the error
            #  and return the existing etag
            etag = await self._storage.get_object_etag(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            )
            return etag.strip('"')
        except Exception as err:
            # Other errors prevent us from drawing a conclusion about interrogation.
            # All we can do is perform cleanup and let the process start over
            raise self.S3OperationError(
                "A unexpected problem occurred trying to complete multipart upload"
                + f" {upload_id} for object {object_id} in the interrogation bucket"
                + f" ({self._interrogation_bucket_id})."
            ) from err

    async def abort_upload(self, *, upload_id: str, object_id: str) -> None:
        """Abort a multipart upload for an object in the interrogation bucket.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        - S3OperationError if an unexpected error occurs while aborting the upload.
        """
        extra = {  # only used for logging
            "upload_id": upload_id,
            "bucket_id": self._interrogation_bucket_id,
            "reencrypted_object_id": object_id,
        }

        try:
            await self._storage.abort_multipart_upload(
                upload_id=upload_id,
                bucket_id=self._interrogation_bucket_id,
                object_id=object_id,
            )
        except ObjectStorageProtocol.BucketNotFoundError as err:
            bucket_error = self.BucketNotFoundError(
                bucket_id=self._interrogation_bucket_id
            )
            raise bucket_error from err
        except ObjectStorageProtocol.MultiPartUploadNotFoundError:
            # If not found, log warning and assume it was already aborted.
            log.warning(
                "Object %s: Tried to abort the multipart upload, but S3 said it"
                + " doesn't exist. This means it was probably aborted already. Nothing"
                + " else needs to be done.",
                object_id,
                extra=extra,
            )
        except Exception as err:
            raise self.S3OperationError(
                f"Failed to abort the multipart upload for object {object_id}."
            ) from err

    async def remove_file(self, *, object_id: str) -> None:
        """Remove a file from the interrogation bucket.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        - S3CleanupError if an unexpected error occurs while deleting the file.
        """
        try:
            await self._storage.delete_object(
                bucket_id=self._interrogation_bucket_id,
                object_id=object_id,
            )
            log.debug(
                "Object %s: Successfully removed from the '%s' bucket.",
                object_id,
                self._interrogation_bucket_id,
            )
        except ObjectStorageProtocol.BucketNotFoundError as err:
            bucket_id = self._interrogation_bucket_id
            bucket_error = self.BucketNotFoundError(bucket_id=bucket_id)
            raise bucket_error from err
        except ObjectStorageProtocol.ObjectNotFoundError:
            # If not found, assume the object was already deleted but log a warning
            log.debug(
                "Object %s: Tried to delete from the '%s' bucket, but appears already deleted.",
                object_id,
                self._interrogation_bucket_id,
            )
        except Exception as err:
            # This error is only logged here, not in the caller
            error = self.S3CleanupError(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            )
            log.error(
                error,
                extra={
                    "bucket_id": self._interrogation_bucket_id,
                    "object_id": object_id,
                },
            )
            raise error from err
