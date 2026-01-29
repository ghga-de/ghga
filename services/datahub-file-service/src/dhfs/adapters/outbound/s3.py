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

"""Outbound adapter that interacts directly with S3 object storage"""

import base64
import logging

import httpx
from async_lru import alru_cache
from hexkit.protocols.objstorage import ObjectStorageProtocol
from pydantic import UUID4
from tenacity import RetryError

from dhfs.adapters.outbound.http import check_for_request_errors
from dhfs.config import Config
from dhfs.constants import (
    DOWNLOAD_URL_CACHE_TIME,
    DOWNLOAD_URL_LIFESPAN,
    URL_CACHE_SIZE,
)
from dhfs.ports.outbound.s3 import S3ClientPort

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

    async def get_is_file_in_inbox(self, *, file_id: UUID4, bucket_id: str) -> bool:
        """Return a bool indicating whether the file exists in the inbox"""
        return await self._storage.does_object_exist(
            bucket_id=bucket_id, object_id=str(file_id)
        )

    async def list_files_in_interrogation_bucket(self) -> list[str]:
        """Returns a list of object IDs from the interrogation bucket.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        """
        try:
            object_ids = await self._storage.list_all_object_ids(
                bucket_id=self._interrogation_bucket_id
            )
            log.info(
                "Retrieved list of %i object IDs from bucket ID '%s'",
                len(object_ids),
                self._interrogation_bucket_id,
            )
            return sorted(object_ids)
        except ObjectStorageProtocol.BucketNotFoundError as err:
            bucket_error = self.BucketNotFoundError(
                f"Failed to get list of files in the {self._interrogation_bucket_id}"
                + " bucket because the bucket doesn't exist."
            )
            log.critical(
                bucket_error,
                exc_info=True,
                extra={"bucket_id": self._interrogation_bucket_id},
            )
            raise bucket_error from err

    @alru_cache(maxsize=URL_CACHE_SIZE, typed=True, ttl=DOWNLOAD_URL_CACHE_TIME)
    async def _get_download_url(self, *, bucket_id: str, object_id: str) -> str:
        """Generate a download URL for an object in the inbox bucket.

        Relies on cache to prevent excessive outbound calls.
        """
        try:
            download_url = await self._storage.get_object_download_url(
                bucket_id=bucket_id,
                object_id=object_id,
                expires_after=DOWNLOAD_URL_LIFESPAN,
            )
            return download_url
        except ObjectStorageProtocol.BucketNotFoundError as err:
            bucket_error = self.BucketNotFoundError(
                f"Cannot get download URL for file {object_id} because"
                + f" the bucket {bucket_id} does not exist."
            )
            log.critical(bucket_error, exc_info=True)
            raise bucket_error from err
        except ObjectStorageProtocol.ObjectNotFoundError as err:
            object_missing_error = self.ObjectNotFoundError(
                f"Cannot get download URL for file {object_id} because it doesn't exist."
            )
            log.error(object_missing_error, exc_info=True)
            raise object_missing_error from err
        except Exception as err:
            error = self.DownloadError(
                "An unexpected error occurred while trying to generate a download URL"
                + f" for file {object_id} in bucket {bucket_id}."
            )
            log.error(error, exc_info=True)
            raise error from err

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
        response = await self._httpx_client.get(download_url, headers=headers)

        status_code = response.status_code
        if status_code in (200, 206):
            return response.content

        if status_code == 403 and not bust_cache:
            log.info(f"Download URL for {object_id} is stale - generating a fresh one")
            return await self.fetch_file_content_range(
                bucket_id=bucket_id,
                object_id=object_id,
                start=start,
                stop=stop,
                bust_cache=True,
            )

        error = self.DownloadError(
            f"Received a {status_code} error when trying to download file {object_id}"
            + f" from bucket {bucket_id}."
        )
        log.error(
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
            log.warning(
                "File %s already exists in interrogation bucket -- deleting"
                + " before beginning interrogation.",
                object_id,
            )
            await self._storage.delete_object(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            )

        try:
            upload_id = await self._storage.init_multipart_upload(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            )
            log.info(
                "Created multipart upload ID %s for file ID %s", upload_id, object_id
            )
            return upload_id
        except ObjectStorageProtocol.MultiPartUploadAlreadyExistsError as err:
            upload_exists_error = self.UploadInitError(
                f"Cannot create a multipart upload for file {object_id} because an"
                + " ongoing upload for the same object already exists."
            )
            log.error(upload_exists_error, exc_info=True)
            raise upload_exists_error from err
        except ObjectStorageProtocol.BucketNotFoundError as err:
            # This is logged as critical because the bucket should definitely exist
            bucket_error = self.BucketNotFoundError(
                f"Cannot create a multipart upload for file {object_id} because"
                + f" the bucket {self._interrogation_bucket_id} does not exist."
            )
            log.critical(bucket_error, exc_info=True)
            raise bucket_error from err
        except Exception as err:
            error = self.UploadInitError(
                "An unexpected error occurred trying to initiate a multipart upload"
                + f" for file {object_id} in bucket {self._interrogation_bucket_id}."
            )
            log.error(error, exc_info=True)
            raise error from err

    async def _get_part_upload_url(
        self,
        *,
        upload_id: str,
        object_id: str,
        part_no: int,
        part_md5: bytes,
    ) -> str:
        """Retrieve a presigned part upload URL for a given file part"""
        # Convert MD5 to base64 for S3
        md5_base64 = base64.b64encode(part_md5).decode()
        try:
            return await self._storage.get_part_upload_url(
                upload_id=upload_id,
                bucket_id=self._interrogation_bucket_id,
                object_id=object_id,
                part_number=part_no,
                part_md5=md5_base64,
            )
        except ObjectStorageProtocol.BucketNotFoundError as err:
            # This is logged as critical because the bucket should definitely exist
            bucket_error = self.BucketNotFoundError(
                f"Failed to get part upload URL for upload {upload_id} because the"
                + f" interrogation bucket {self._interrogation_bucket_id} does not exist."
            )
            log.critical(
                bucket_error,
                exc_info=True,
                extra={
                    "upload_id": upload_id,
                    "object_id": object_id,
                    "part_no": part_no,
                },
            )
            raise bucket_error from err
        except ObjectStorageProtocol.MultiPartUploadNotFoundError as err:
            error = self.UploadPartError(
                f"Failed to get part upload URL for upload {upload_id} because the"
                + " upload does not exist."
            )
            log.critical(
                error,
                exc_info=True,
                extra={
                    "upload_id": upload_id,
                    "object_id": object_id,
                    "part_no": part_no,
                },
            )
            raise error from err

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
        - UploadError if any other error causes the part upload to fail.
        """
        upload_url = await self._get_part_upload_url(
            upload_id=upload_id,
            object_id=object_id,
            part_no=part_no,
            part_md5=part_md5,
        )

        try:
            log.debug("Uploading file part number %i for %s", part_no, object_id)
            response = await self._httpx_client.put(upload_url, content=part)
        except RetryError as retry_error:
            check_for_request_errors(retry_error, upload_url)
            response = retry_error.last_attempt.result()

        if response.status_code != 200:
            status_code = response.status_code

            if status_code == 400:
                # A bad MD5 means that uploading the re-encrypted file has failed
                md5_error = self.BadPartMD5Error(part_no=part_no, object_id=object_id)
                log.error(md5_error)
                raise md5_error
            else:
                detail = response.content.decode()
                upload_error = self.UploadPartError(
                    f"Failed to upload part {part_no} for file {object_id}. Status"
                    + f" code is {response.status_code}. Detail: {detail}"
                )
                log.error(upload_error)
                raise upload_error

    async def complete_upload(
        self, *, upload_id: str, object_id: str, part_count: int
    ) -> str:
        """Complete a multipart upload for an object in the interrogation bucket.

        Returns the object's ETag (which is the MD5 checksum of the encrypted file).

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        - PartCountMismatchError if the number of uploaded parts doesn't match the expected count.
        - UploadCompletionError if the upload doesn't exist or another error prevents completion.
        """
        extra = {  # for logging purposes
            "upload_id": upload_id,
            "bucket_id": self._interrogation_bucket_id,
            "object_id": object_id,
            "part_count": part_count,
        }
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
            # This is logged as critical because the bucket should definitely exist
            # At the completion stage, this shouldn't happen. Initiating and concluding
            #  the MPU have to occur in the same service instance lifetime, so bad
            #  bucket config should have been caught when starting interrogation.
            # We have no choice here but to perform cleanup and raise an error.
            bucket_error = self.BucketNotFoundError(
                f"Couldn't complete upload {upload_id} for file {object_id} because"
                + f" the bucket {self._interrogation_bucket_id} does not exist."
            )
            log.critical(bucket_error, exc_info=True, extra=extra)
            raise bucket_error from err
        except ObjectStorageProtocol.MultiPartUploadConfirmError as err:
            # In this case, the Interrogator needs to know that interrogation has failed
            #  but the S3 client can proactively perform cleanup
            part_count_error = self.PartCountMismatchError(
                upload_id=upload_id, object_id=object_id, part_count=part_count
            )
            log.error(part_count_error, exc_info=True, extra=extra)
            raise part_count_error from err
        except ObjectStorageProtocol.MultiPartUploadNotFoundError as err:
            # This isn't as critical as the BucketNotFoundError as it's not a config issue.
            if not await self._storage.does_object_exist(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            ):
                error = self.UploadCompletionError(
                    f"Couldn't complete upload {upload_id} for file {object_id} because"
                    + " the upload doesn't exist. No cleanup required.",
                )
                log.error(error, exc_info=True, extra=extra)
                raise error from err
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
            error = self.UploadCompletionError(
                f"A problem occurred trying to complete multipart upload {upload_id}"
                + f" for file {object_id} in the interrogation bucket"
                + f" ({self._interrogation_bucket_id})."
            )
            log.error(error, exc_info=True, extra=extra)
            raise error from err

    async def abort_upload(self, *, upload_id: str, object_id: str) -> None:
        """Abort a multipart upload for an object in the interrogation bucket.

        Raises:
        - BucketNotFoundError if the interrogation bucket doesn't exist.
        - S3Error if an unexpected error occurs while aborting the upload.
        """
        extra = {  # only used for logging
            "upload_id": upload_id,
            "bucket_id": self._interrogation_bucket_id,
            "object_id": object_id,
        }

        try:
            await self._storage.abort_multipart_upload(
                upload_id=upload_id,
                bucket_id=self._interrogation_bucket_id,
                object_id=object_id,
            )
        except ObjectStorageProtocol.BucketNotFoundError as err:
            # This is logged as critical because the bucket should definitely exist
            bucket_error = self.BucketNotFoundError(
                f"Couldn't abort upload {upload_id} for file {object_id} because"
                + f" the bucket {self._interrogation_bucket_id} does not exist."
            )
            log.critical(bucket_error, exc_info=True, extra=extra)
            raise bucket_error from err
        except ObjectStorageProtocol.MultiPartUploadNotFoundError:
            # If not found, log warning and assume it was already aborted.
            log.warning(
                "Tried to abort multipart upload with ID %s (for file %s), but S3 said it doesn't exist.",
                upload_id,
                object_id,
            )
        except Exception as err:
            error = self.S3Error(
                f"Failed to abort multipart upload {upload_id} for file {object_id}"
                + f" in the interrogation bucket ({self._interrogation_bucket_id})."
            )
            log.error(
                error,
                exc_info=True,
                extra=extra,
            )
            raise error from err

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
            log.info(
                "Successfully removed %s from bucket ID %s",
                object_id,
                self._interrogation_bucket_id,
            )
        except ObjectStorageProtocol.BucketNotFoundError as err:
            # This is logged as critical because the bucket should definitely exist
            bucket_id = self._interrogation_bucket_id
            bucket_error = self.BucketNotFoundError(
                f"The bucket {bucket_id} was not found while trying to remove"
                + f" file {object_id}. This error should not have occurred."
            )
            log.critical(
                bucket_error,
                exc_info=True,
                extra={"bucket_id": bucket_id, "object_id": object_id},
            )
            raise bucket_error from err
        except ObjectStorageProtocol.ObjectNotFoundError:
            # If not found, assume the object was already deleted but log a warning
            log.warning(
                "Tried to delete file %s from bucket %s, but it's already deleted",
                object_id,
                self._interrogation_bucket_id,
            )
        except Exception as err:
            error = self.S3CleanupError(
                bucket_id=self._interrogation_bucket_id, object_id=object_id
            )
            log.error(
                error,
                exc_info=True,
                extra={
                    "bucket_id": self._interrogation_bucket_id,
                    "object_id": object_id,
                },
            )
            raise error from err
