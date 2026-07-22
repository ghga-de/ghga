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
"""Upload functionality"""

import asyncio
import logging

from pydantic import UUID4

from ghga_connector.constants import (
    MAX_RETRIES,
    MAX_UPLOAD_BACKOFF_SEC,
    UPLOAD_RETRY_BACKOFF_SEC,
)
from ghga_connector.core.crypt.encryption import Crypt4GHEncryptor, FileProcessor
from ghga_connector.core.progress_bar import UploadProgressBar
from ghga_connector.core.tasks import TaskHandler
from ghga_connector.core.uploading.api_calls import UploadClient
from ghga_connector.core.uploading.structs import FileInfoForUpload
from ghga_connector.exceptions import (
    CompleteFileUploadError,
    CreateFileUploadError,
    DeleteFileUploadError,
    TooManyRequestsError,
    UploadFileError,
)

log = logging.getLogger(__name__)


class Uploader:
    """Provides the functionality to upload a single file"""

    def __init__(
        self,
        *,
        upload_client: UploadClient,
        file_info: FileInfoForUpload,
        max_concurrent_uploads: int,
        display_name: str | None = None,
        overwrite: bool = False,
    ):
        """Instantiate the Uploader.

        ``display_name`` is used only for the progress bar label; if omitted, the file
        alias is used. The alias sent to the Upload API is always the full alias.

        If `overwrite` is True, each uploaded file replaces any existing FileUpload for
        its alias as long as it has not reached the "interrogated" state (re-encrypted).
        """
        self._upload_client = upload_client
        self._file_alias = file_info.alias
        self._display_name = display_name or file_info.alias
        self._file_path = file_info.path
        self._file_info = file_info
        self._overwrite = overwrite
        self._semaphore = asyncio.Semaphore(max_concurrent_uploads)

    def new_progress_bar(self) -> UploadProgressBar:
        """Create a new progress bar"""
        return UploadProgressBar(
            file_name=self._display_name, file_size=self._file_info.decrypted_size
        )

    async def initiate_file_upload(
        self, *, tries_left: int = MAX_RETRIES
    ) -> tuple[UUID4, str]:
        """Initiate a file upload in the Upload API, exchanging the file alias for a
        UUID4 file ID and storage alias.

        Raises a `CreateFileUploadError` if the operation fails.
        """
        # Establish the file expectation and open the multipart upload
        try:
            self._file_id, storage_alias = await self._upload_client.create_file_upload(
                file_alias=self._file_alias,
                decrypted_size=self._file_info.decrypted_size,
                encrypted_size=self._file_info.encrypted_size,
                part_size=self._file_info.part_size,
                overwrite=self._overwrite,
            )
            return self._file_id, storage_alias
        except TooManyRequestsError as exc:
            # Files are currently processed sequentially - a 429 might mean
            #  some transient lag in UCS in updating FileUpload state after uploading or
            #  perhaps parallel Connector usage by the submitter.
            #  Perform a few retries before letting the error bubble up
            if tries_left:
                times_already_retried = MAX_RETRIES - tries_left
                await asyncio.sleep(
                    min(
                        UPLOAD_RETRY_BACKOFF_SEC * (2**times_already_retried),
                        MAX_UPLOAD_BACKOFF_SEC,
                    )
                )
                return await self.initiate_file_upload(tries_left=tries_left - 1)
            raise CreateFileUploadError(
                file_alias=self._file_alias,
                exception=exc,
            ) from exc
        except Exception as exc:
            raise CreateFileUploadError(
                file_alias=self._file_alias,
                exception=exc,
            ) from exc

    async def delete_file(self) -> None:
        """Delete a file from its FileUploadBox

        Raises a `FileDeletionError` if there's a problem with the operation.
        """
        try:
            await self._upload_client.delete_file(
                file_id=self._file_id, file_alias=self._file_alias
            )
        except Exception as exc:
            raise DeleteFileUploadError(
                file_alias=self._file_alias,
                file_id=self._file_id,
                exception=exc,
            ) from exc

    async def _upload_file_part(self, file_processor: FileProcessor) -> None:
        """Encrypt and upload a file part.

        Fetches the next part from the file_processor.

        Raises:
            UploadFileError: If there is a problem during content transfer.
            CancelledError: If the task is cancelled.
            RequestFailedError: If the request fails without returning a response code.
            UnexpectedError: If the status code is not 200.
        """
        async with self._semaphore:
            part_number = 0  # defined here so it can be used in the exception
            try:
                part_number, part = next(file_processor)
                await self._upload_client.upload_file_part(
                    file_id=self._file_id, content=part, part_no=part_number
                )
                self._progress_bar.advance(len(part))  # Created in `.upload_file()`
                self._in_sequence_part_number += 1

            except BaseException as exc:
                # correctly reraise CancelledError, else this might get stuck waiting
                # on semaphore lock release
                if isinstance(exc, asyncio.CancelledError):
                    raise
                raise UploadFileError(
                    file_alias=self._file_alias,
                    exception=exc,
                ) from exc

    async def upload_file(self, *, encryptor: Crypt4GHEncryptor):
        """Upload a file to S3, encrypting it on the fly.

        Raises:
            UploadFileError: If there's a problem during actual file upload.
            EncryptedSizeMismatch: If the actual size of the encrypted file doesn't
                match the expected value.
            CompleteFileUploadError: If there's an error completing the file upload.
        """
        self._in_sequence_part_number = 1

        # Encrypt and upload file parts in parallel
        self._progress_bar = self.new_progress_bar()
        with self._file_path.open("rb") as file, self._progress_bar:
            file_processor = encryptor.process_file(file=file)
            task_handler = TaskHandler()
            for _ in range(self._file_info.part_count):
                task_handler.schedule(
                    self._upload_file_part(file_processor=file_processor)
                )
            # Wait for all upload tasks to finish
            await task_handler.gather()

        # Get the unencrypted checksum and tell the Upload API to conclude the S3 upload
        unencrypted_checksum = encryptor.checksums.decrypted_sha256.hexdigest()
        encrypted_checksum = encryptor.checksums.get_encrypted_checksum_for_s3()

        try:
            await self._upload_client.complete_file_upload(
                file_id=self._file_id,
                file_alias=self._file_alias,
                decrypted_sha256=unencrypted_checksum,
                encrypted_md5=encrypted_checksum,
                encrypted_parts_md5=encryptor.checksums.encrypted_parts_md5,
                encrypted_parts_sha256=encryptor.checksums.encrypted_parts_sha256,
            )
            log.info("(4/4) Finished upload for %s.", self._file_id)
        except Exception as exc:
            raise CompleteFileUploadError(
                file_alias=self._file_alias,
                exception=exc,
            ) from exc
