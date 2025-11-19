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
"""Upload functionality"""

import asyncio
import logging

from pydantic import UUID4

from ghga_connector import exceptions
from ghga_connector.core.crypt.encryption import Crypt4GHEncryptor, FileProcessor
from ghga_connector.core.progress_bar import UploadProgressBar
from ghga_connector.core.tasks import TaskHandler
from ghga_connector.core.uploading.api_calls import UploadClient
from ghga_connector.core.uploading.structs import FileInfoForUpload
from ghga_connector.core.utils import calc_number_of_parts

log = logging.getLogger(__name__)


class Uploader:
    """Provides the functionality to upload a single file"""

    def __init__(
        self,
        *,
        upload_client: UploadClient,
        encryptor: Crypt4GHEncryptor,
        file_info: FileInfoForUpload,
        part_size: int,
        max_concurrent_uploads: int,
    ):
        """Instantiate the Uploader"""
        self._upload_client = upload_client
        self._file_alias = file_info.alias
        self._file_path = file_info.path
        self._encryptor = encryptor
        self._part_size = part_size
        self._file_size = file_info.size
        self._semaphore = asyncio.Semaphore(max_concurrent_uploads)

    def new_progress_bar(self) -> UploadProgressBar:
        """Create a new progress bar"""
        return UploadProgressBar(file_name=self._file_alias, file_size=self._file_size)

    async def initiate_file_upload(self) -> UUID4:
        """Initiate a file upload in the Upload API, exchanging the file alias for a
        UUID4 file ID.

        Raises a `CreateFileUploadError` if the operation fails.
        """
        # Establish the file expectation and open the multipart upload
        try:
            self._file_id = await self._upload_client.create_file_upload(
                file_alias=self._file_alias, file_size=self._file_size
            )
            return self._file_id
        except Exception as err:
            raise exceptions.CreateFileUploadError(
                file_alias=self._file_alias, reason=str(err)
            ) from err

    async def delete_file(self) -> None:
        """Delete a file from its FileUploadBox

        Raises a `FileDeletionError` if there's a problem with the operation.
        """
        try:
            await self._upload_client.delete_file(file_id=self._file_id)
        except Exception as err:
            raise exceptions.DeleteFileUploadError(
                file_alias=self._file_alias, file_id=self._file_id, reason=str(err)
            ) from err

    async def _upload_file_part(self, file_processor: FileProcessor) -> None:
        """Encrypt and upload a file part

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
                raise exceptions.UploadFileError(
                    file_alias=self._file_alias, reason=str(exc)
                ) from exc

    async def upload_file(self):
        """Upload a file to S3, encrypting it on the fly.

        Raises:
            UploadFileError: If there's a problem during actual file upload.
            EncryptedSizeMismatch: If the actual size of the encrypted file doesn't
                match the expected value.
            CompleteFileUploadError: If there's an error completing the file upload.
        """
        num_parts = calc_number_of_parts(
            self._encryptor.expected_encrypted_size, self._part_size
        )
        self._in_sequence_part_number = 1

        # Encrypt and upload file parts in parallel
        self._progress_bar = self.new_progress_bar()
        with self._file_path.open("rb") as file, self._progress_bar:
            file_processor = self._encryptor.process_file(file=file)
            task_handler = TaskHandler()
            for _ in range(num_parts):
                task_handler.schedule(
                    self._upload_file_part(file_processor=file_processor)
                )
            # Wait for all upload tasks to finish
            await task_handler.gather()

        # Get the unencrypted checksum and tell the Upload API to conclude the S3 upload
        unencrypted_checksum = self._encryptor.checksums.unencrypted_sha256.hexdigest()
        encrypted_checksum = self._encryptor.checksums.encrypted_checksum_for_s3()

        try:
            await self._upload_client.complete_file_upload(
                file_id=self._file_id,
                unencrypted_checksum=unencrypted_checksum,
                encrypted_checksum=encrypted_checksum,
            )
            log.info("(4/4) Finished upload for %s.", self._file_id)
        except Exception as err:
            raise exceptions.CompleteFileUploadError(
                file_alias=self._file_alias, reason=str(err)
            ) from err
