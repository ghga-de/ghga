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
#
"""Contains a concrete implementation of the abstract downloader"""

import asyncio
import gc
import logging
from asyncio import PriorityQueue, Queue, Semaphore, Task
from contextlib import contextmanager
from io import BufferedWriter
from pathlib import Path

from ghga_connector import exceptions
from ghga_connector.core import CLIMessageDisplay, PartRange, calc_part_ranges
from ghga_connector.core.tasks import TaskHandler

from ..progress_bar import DownloadProgressBar
from .api_calls import DownloadClient, extract_download_url
from .structs import FileInfo, RetryResponse

logger = logging.getLogger(__name__)
# TODO: [later] More better logging

__all__ = ["Downloader", "handle_download_errors"]


@contextmanager
def handle_download_errors(file_info: FileInfo):
    """Used to handle download errors from `Downloader.download_file()`"""
    file_id = file_info.file_id
    try:
        yield
    except exceptions.GetEnvelopeError as error:
        CLIMessageDisplay.failure(
            f"The request to get an envelope for file '{file_id}' failed."
        )
        raise error
    except exceptions.DownloadError as error:
        CLIMessageDisplay.failure(f"Failed downloading with id '{file_id}'.")
        raise error


class Downloader:
    """Centralized high-level interface for downloading a single file.

    This is not meant to be reused, as internal state is not cleared.
    """

    def __init__(
        self,
        *,
        download_client: DownloadClient,
        file_id: str,
        file_size: int,
        max_concurrent_downloads: int,
    ):
        self._download_client = download_client
        self._file_id = file_id
        self._file_size = file_size
        self._queue: Queue[tuple[int, bytes]] = PriorityQueue()
        self._semaphore = Semaphore(value=max_concurrent_downloads)
        self._task_handler = TaskHandler()

    async def download_file(self, *, output_path: Path, part_size: int):
        """Download file to the specified location and manage lower level details.

        The process is, roughly:
        - Retrieve file envelope
        - Schedule a download task for every file part
        - Write file parts to disk as they're completed
        """
        # Split the file into parts based on the part size
        CLIMessageDisplay.display(
            f"Fetching work order token and download URL for {self._file_id}"
        )
        logger.debug("Initial fetch of download URL for file %s", self._file_id)
        part_ranges = calc_part_ranges(
            part_size=part_size, total_file_size=self._file_size
        )

        # get file header envelope
        logger.debug("Fetching Crypt4GH envelope for file %s", self._file_id)
        try:
            envelope = await self._download_client.get_file_envelope(
                file_id=self._file_id
            )
        except (
            exceptions.FileNotRegisteredError,
            exceptions.BadResponseCodeError,
        ) as error:
            raise exceptions.GetEnvelopeError() from error

        # start async part download to intermediate queue
        logger.debug("Scheduling download for file %s", self._file_id)
        for part_range in part_ranges:
            self._task_handler.schedule(self._download_to_queue(part_range=part_range))

        logger.debug(
            "Current amount of download tasks after scheduling: %i",
            len([task for task in asyncio.all_tasks() if not task.done()]),
        )

        # Write the downloaded parts to a file
        with output_path.open("wb") as file:
            # put envelope in file
            logger.debug("Writing Crypt4GH envelope for file %s", self._file_id)
            file.write(envelope)
            # start download task
            logger.debug("Starting to write file parts to disk for %s", self._file_id)
            write_to_file = Task(
                self._drain_queue_to_file(
                    file=file,
                    file_size=self._file_size,
                    offset=len(envelope),
                ),
                name="Write queue to file",
            )
            try:
                await self._task_handler.gather()
            except:
                write_to_file.cancel()
                raise
            else:
                await write_to_file

    async def fetch_download_url(self, bust_cache: bool = False) -> str:
        """Retrieve the download URL.

        Uses the DownloadClient to get the DRS object from the Download API, then
        extracts the presigned S3 download URL from the DRS object.

        Raises:
            NoS3AccessMethodError: If the DRS object for the file doesn't have an S3
                access method.
            RequestFailedError: If the file download fails.
            UnexpectedRetryResponseError: If the file still isn't staged to the download
                bucket in object storage even though it should be.
        """
        try:
            drs_object = await self._download_client.get_drs_object(
                self._file_id, bust_cache=bust_cache
            )
        except exceptions.BadResponseCodeError as err:
            CLIMessageDisplay.failure(
                f"The request for file {self._file_id} returned an unexpected HTTP status code: {err.response_code}."
            )
            raise
        except exceptions.RequestFailedError:
            CLIMessageDisplay.failure(
                f"The download request for file {self._file_id} failed."
            )
            raise

        # If the Download API returns a RetryResponse, it means the S3 object has not
        #  yet been staged or made available for download from the proper S3 bucket.
        if isinstance(drs_object, RetryResponse):
            # At this point, the file should definitely be staged -- raise an error
            raise exceptions.UnexpectedRetryResponseError()

        # Extract the actual download URL from the DRS object received from the Download API
        download_url = extract_download_url(drs_object)
        return download_url

    async def _download_to_queue(self, *, part_range: PartRange) -> None:
        """
        Start downloading file parts in parallel into a queue.
        This should be wrapped into an asyncio.task and is guarded by a semaphore to
        limit the amount of ongoing parallel downloads to max_concurrent_downloads.
        """
        # Guard with semaphore to ensure only a set amount of downloads runs in parallel
        async with self._semaphore:
            download_url = await self.fetch_download_url()
            try:
                try:
                    offset, bytes = await self._download_client.download_content_range(
                        url=download_url, start=part_range.start, end=part_range.stop
                    )
                    await self._queue.put((offset, bytes))
                except exceptions.UnauthorizedAPICallError:
                    # For clarity, this means the S3 URL was expired
                    download_url = await self.fetch_download_url(bust_cache=True)
                    logger.debug(
                        "Encountered 403, trying again with new URL: %s", download_url
                    )
                    offset, bytes = await self._download_client.download_content_range(
                        url=download_url, start=part_range.start, end=part_range.stop
                    )
                    await self._queue.put((offset, bytes))
            except Exception as exception:
                raise exceptions.DownloadError(reason=str(exception)) from exception

    async def _drain_queue_to_file(
        self,
        *,
        file: BufferedWriter,
        file_size: int,
        offset: int,
    ) -> None:
        """Write downloaded file bytes from queue.
        This should be started as asyncio.Task and awaited after the download_to_queue
        tasks have been created/started.
        """
        # track and display actually written bytes
        downloaded_size = 0

        with DownloadProgressBar(
            file_name=file.name, file_size=file_size
        ) as progress_bar:
            while downloaded_size < file_size:
                result = await self._queue.get()
                start, part = result
                file.seek(offset + start)
                file.write(part)
                # update tracking information
                chunk_size = len(part)
                downloaded_size += chunk_size
                self._queue.task_done()
                progress_bar.advance(chunk_size)
                gc.collect()
