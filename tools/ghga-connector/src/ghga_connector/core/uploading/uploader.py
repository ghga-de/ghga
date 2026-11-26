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
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractAsyncContextManager
from typing import Any

from pydantic import UUID4

from ghga_connector.constants import (
    MAX_RETRIES,
    MAX_UPLOAD_BACKOFF_SEC,
    UPLOAD_RETRY_BACKOFF_SEC,
)
from ghga_connector.core.crypt.checksums import Checksums, md5_hex, sha256_hex
from ghga_connector.core.crypt.encryption import Crypt4GHEncryptor, FileProcessor
from ghga_connector.core.progress_bar import (
    BatchUploadProgress,
    FileProgressRow,
    UploadProgressBar,
)
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


def _discard(task: asyncio.Task) -> None:
    """Cancel a task whose result is no longer needed, and collect any error it raised.

    Collecting the error keeps asyncio from logging it as never retrieved.
    """
    task.cancel()
    task.add_done_callback(lambda done: done.cancelled() or done.exception())


class FairSlots:
    """A part slot from the batch's budget, at most `per_file` of them for this file.

    A part first takes one of its file's slots, then one of the batch's, so a batch
    slot only goes to a part its file may send. asyncio's semaphores wake waiting
    tasks in the order they arrived, so the batch slots go to the files in turn.
    """

    def __init__(self, budget: asyncio.Semaphore, per_file: int):
        self._budget = budget
        self._own = asyncio.Semaphore(per_file)
        self._per_file = per_file

    def widen(self, per_file: int) -> None:
        """Raise the file's share, for when fewer files are left in flight."""
        for _ in range(per_file - self._per_file):
            self._own.release()
        self._per_file = max(self._per_file, per_file)

    async def __aenter__(self) -> None:
        """Take one of the file's slots, then one of the batch's."""
        await self._own.acquire()
        try:
            await self._budget.acquire()
        except BaseException:
            self._own.release()
            raise

    async def __aexit__(self, *exc_info: object) -> None:
        """Give both slots back."""
        self._budget.release()
        self._own.release()


class Uploader:
    """Provides the functionality to upload a single file"""

    def __init__(  # noqa: PLR0913
        self,
        *,
        upload_client: UploadClient,
        file_info: FileInfoForUpload,
        part_slots: AbstractAsyncContextManager[Any],
        display_name: str | None = None,
        overwrite: bool = False,
        progress: BatchUploadProgress | None = None,
    ):
        """Instantiate the Uploader.

        Each part holds one of ``part_slots`` from before its encryption until its
        upload and hashes are done, which bounds the parts in memory. A batch passes
        its `FairSlots`; a semaphore works too.

        ``display_name`` is used only for the progress bar label; if omitted, the file
        alias is used. The alias sent to the Upload API is always the full alias. With
        ``progress``, the file gets a row in that shared display instead of its own bar.

        If `overwrite` is True, each uploaded file replaces any existing FileUpload for
        its alias as long as it has not reached the "interrogated" state (re-encrypted).
        """
        self._upload_client = upload_client
        self._file_alias = file_info.alias
        self._display_name = display_name or file_info.alias
        self._file_path = file_info.path
        self._file_info = file_info
        self._overwrite = overwrite
        self._part_slots = part_slots
        self._progress = progress
        # How many parts were handed to the encryption worker; see `_upload_file_part`
        self._parts_submitted = 0

    def new_progress_bar(self) -> UploadProgressBar | FileProgressRow:
        """Create a new progress bar, or a row in the batch's shared display"""
        if self._progress is not None:
            return self._progress.file_row(
                self._display_name, self._file_info.decrypted_size
            )
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
            # UCS limits the open uploads per box, which counts this run's files in
            #  flight, uploads left by stopped runs and other Connectors on the box.
            #  It may also lag in updating a FileUpload's state after its upload.
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

    async def _encrypt_next_part(
        self, file_processor: FileProcessor, encryption_pool: ThreadPoolExecutor
    ) -> tuple[int, bytearray] | None:
        """Advance the file processor on the encryption worker, off the event loop.

        The single worker is what keeps the shared processor from being advanced
        concurrently. `next` gets a default because StopIteration cannot be raised
        into a Future.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(encryption_pool, next, file_processor, None)

    async def _upload_file_part(
        self, file_processor: FileProcessor, encryption_pool: ThreadPoolExecutor
    ) -> None:
        """Encrypt and upload a file part.

        Fetches the next part from the file_processor. The part's URL is requested
        while the part is encrypted: the single encryption worker serves the parts in
        the order they were asked for, so the n-th request yields part n. Should the
        number differ, the URL is dropped and the upload fetches the right one. The
        part's MD5 and SHA-256 are computed in threads while it uploads, and recorded
        once both are done.

        Raises:
            UploadFileError: If there is a problem during content transfer.
            CancelledError: If the task is cancelled.
            RequestFailedError: If the request fails without returning a response code.
            UnexpectedError: If the status code is not 200.
        """
        async with self._part_slots:
            part_number = 0  # defined here so it can be used in the exception
            try:
                self._parts_submitted += 1
                expected_number = self._parts_submitted
                url_task = asyncio.create_task(
                    self._upload_client.get_part_upload_url(
                        file_id=self._file_id, part_no=expected_number
                    )
                )
                try:
                    next_part = await self._encrypt_next_part(
                        file_processor, encryption_pool
                    )
                except BaseException:
                    _discard(url_task)
                    raise
                if next_part is None:
                    _discard(url_task)
                    raise RuntimeError(
                        "The file processor ran out of parts before all scheduled part"
                        + " uploads were performed."
                    )
                part_number, part = next_part
                url = None
                if part_number == expected_number:
                    url = await url_task
                else:
                    _discard(url_task)
                md5, sha256, _ = await asyncio.gather(
                    asyncio.to_thread(md5_hex, part),
                    asyncio.to_thread(sha256_hex, part),
                    self._upload_client.upload_file_part(
                        file_id=self._file_id,
                        content=part,
                        part_no=part_number,
                        url=url,
                    ),
                )
                # Both are set in `.upload_file()`
                self._checksums.set_part(part_number, md5=md5, sha256=sha256)
                self._progress_bar.advance(len(part))

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
            CiphertextSizeMismatch: If the actual size of the encrypted file doesn't
                match the expected value.
            CompleteFileUploadError: If there's an error completing the file upload.
        """
        # Encrypt and upload file parts in parallel
        self._checksums: Checksums = encryptor.checksums
        self._parts_submitted = 0
        self._progress_bar = self.new_progress_bar()
        with self._file_path.open("rb") as file, self._progress_bar:
            encryption_pool = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="crypt4gh"
            )
            try:
                file_processor = encryptor.process_file(file=file)
                task_handler = TaskHandler()
                for _ in range(self._file_info.part_count):
                    task_handler.schedule(
                        self._upload_file_part(
                            file_processor=file_processor,
                            encryption_pool=encryption_pool,
                        )
                    )
                # Wait for all upload tasks to finish
                await task_handler.gather()

                # The processor is suspended at its final `yield`; advancing it
                # once more runs its trailing ciphertext size validation.
                surplus_part = await self._encrypt_next_part(
                    file_processor, encryption_pool
                )
                if surplus_part is not None:
                    raise RuntimeError(
                        "The file processor produced more parts than the"
                        + f" {self._file_info.part_count} that were uploaded."
                    )
            finally:
                # Let the in-flight encryption finish before the file closes,
                # so a failed upload cannot stall interpreter shutdown.
                encryption_pool.shutdown(wait=True, cancel_futures=True)

        # Every part must have its hashes, or the checksums sent below are wrong
        expected_parts = list(range(1, self._file_info.part_count + 1))
        if self._checksums.part_numbers != expected_parts:
            raise RuntimeError(
                f"The checksums of parts {self._checksums.part_numbers} do not match"
                + f" the {self._file_info.part_count} parts that were uploaded."
            )

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
