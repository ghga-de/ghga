# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
import base64
import gc
from asyncio import PriorityQueue, Queue, Semaphore, Task, create_task
from collections.abc import Coroutine
from io import BufferedWriter
from pathlib import Path
from typing import Any

import httpx
from tenacity import RetryError

from ghga_connector.core import (
    AbstractMessageDisplay,
    PartRange,
    ResponseExceptionTranslator,
    WorkPackageAccessor,
    calc_part_ranges,
    exceptions,
    retry_handler,
)

from .abstract_downloader import DownloaderBase
from .api_calls import (
    get_download_url,
    get_envelope_authorization,
    get_file_authorization,
)
from .progress_bar import ProgressBar
from .structs import RetryResponse, URLResponse


class TaskHandler:
    """Wraps task scheduling details."""

    def __init__(self):
        self._tasks: set[Task] = set()

    def schedule(self, fn: Coroutine[Any, Any, None]):
        """Create a task and register its callback."""
        task = create_task(fn)
        self._tasks.add(task)
        task.add_done_callback(self.finalize)

    def cancel_tasks(self):
        """Cancel all running taks."""
        for task in self._tasks:
            if not task.done():
                task.cancel()

    def finalize(self, task: Task):
        """Deal with potential errors when a task is done.

        This is called as done callback, so there are three possibilites here:
        1. A task encountered an exception: Cancel all remaining tasks and reraise
        2. A task was cancelled: There's nothing to do, we are already propagating
           the exception causing the cancellation
        3. A task finished normally: Remove its handle
        """
        if not task.cancelled():
            exception = task.exception()
            if exception:
                self.cancel_tasks()
                raise exception
        self._tasks.discard(task)

    async def gather(self):
        """Await all remaining tasks."""
        await asyncio.gather(*self._tasks)


class Downloader(DownloaderBase):
    """Centralized high-level interface for download functionality. Used in the core.
    This is not meant to be reused, as internal state is not cleared.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        client: httpx.AsyncClient,
        file_id: str,
        max_concurrent_downloads: int,
        max_wait_time: int,
        message_display: AbstractMessageDisplay,
        work_package_accessor: WorkPackageAccessor,
    ):
        self._client = client
        self._file_id = file_id
        self._max_wait_time = max_wait_time
        self._message_display = message_display
        self._work_package_accessor = work_package_accessor
        self._queue: Queue[tuple[int, bytes]] = PriorityQueue()
        self._semaphore = Semaphore(value=max_concurrent_downloads)

    async def download_file(self, *, output_path: Path, part_size: int):
        """Download file to the specified location and manage lower level details."""
        # Split the file into parts based on the part size
        self._message_display.display(
            f"Fetching work order token and download URL for {self._file_id}"
        )
        url_response = await self.fetch_download_url()
        part_ranges = calc_part_ranges(
            part_size=part_size, total_file_size=url_response.file_size
        )

        task_handler = TaskHandler()

        # start async part download to intermediate queue
        for part_range in part_ranges:
            task_handler.schedule(self.download_to_queue(part_range=part_range))

        # get file header envelope
        try:
            envelope = await self.get_file_header_envelope()
        except (
            exceptions.FileNotRegisteredError,
            exceptions.EnvelopeNotFoundError,
            exceptions.ExternalApiError,
        ) as error:
            # Cancel running tasks before raising
            task_handler.cancel_tasks()
            raise exceptions.GetEnvelopeError() from error

        # Write the downloaded parts to a file
        with (
            output_path.open("wb") as file,
            ProgressBar(
                file_name=file.name, file_size=url_response.file_size
            ) as progress_bar,
        ):
            # put envelope in file
            file.write(envelope)
            # start download task
            write_to_file = Task(
                self.drain_queue_to_file(
                    file=file,
                    file_size=url_response.file_size,
                    offset=len(envelope),
                    progress_bar=progress_bar,
                ),
                name="Write queue to file",
            )
            try:
                await task_handler.gather()
            except:
                write_to_file.cancel()
                raise
            else:
                await write_to_file

    async def fetch_download_url(self) -> URLResponse:
        """Fetch a work order token and retrieve the download url.

        Returns a URLResponse containing two elements:
            1. the download url
            2. the file size in bytes
        """
        try:
            url_and_headers = await get_file_authorization(
                file_id=self._file_id,
                work_package_accessor=self._work_package_accessor,
            )
            response = await get_download_url(
                client=self._client, url_and_headers=url_and_headers
            )
        except exceptions.BadResponseCodeError as error:
            self._message_display.failure(
                f"The request for file {self._file_id} returned an unexpected HTTP status code: {error.response_code}."
            )
            raise error
        except exceptions.RequestFailedError as error:
            self._message_display.failure(
                f"The download request for file {self._file_id} failed."
            )
            raise error

        if isinstance(response, RetryResponse):
            # File should be staged at that point in time
            raise exceptions.UnexpectedRetryResponseError()

        return response

    async def get_file_header_envelope(self) -> bytes:
        """
        Perform a RESTful API call to retrieve a file header envelope.
        Returns:
            The file header envelope (bytes object)
        """
        url_and_headers = await get_envelope_authorization(
            file_id=self._file_id, work_package_accessor=self._work_package_accessor
        )
        url = url_and_headers.endpoint_url
        # Make function call to get download url
        try:
            response = await self._client.get(url=url, headers=url_and_headers.headers)
        except httpx.RequestError as request_error:
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code

        if status_code == 200:
            return base64.b64decode(response.content)

        # For now unauthorized responses are not handled by httpyexpect
        if status_code == 403:
            content = response.json()
            # handle both normal and httpyexpect 403 response
            try:
                cause = content["description"]
            except KeyError:
                cause = content["detail"]
            raise exceptions.UnauthorizedAPICallError(url=url, cause=cause)

        spec = {
            404: {
                "envelopeNotFoundError": lambda: exceptions.EnvelopeNotFoundError(
                    file_id=self._file_id
                ),
                "noSuchObject": lambda: exceptions.FileNotRegisteredError(
                    file_id=self._file_id
                ),
            },
            500: {"externalAPIError": exceptions.ExternalApiError},
        }

        ResponseExceptionTranslator(spec=spec).handle(response=response)
        raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

    async def download_to_queue(self, *, part_range: PartRange) -> None:
        """
        Start downloading file parts in parallel into a queue.
        This should be wrapped into  asyncio.task and is guarded by a semaphore to limit
        the amount of ongoing parallel downloads to max_concurrent_downloads.
        """
        # Guard with semaphore to ensure only a set amount of downloads runs in parallel
        async with self._semaphore:
            url_and_headers = await self.fetch_download_url()
            url = url_and_headers.download_url
            try:
                await self.download_content_range(
                    url=url, start=part_range.start, end=part_range.stop
                )
            except Exception as exception:
                raise exceptions.DownloadError(reason=str(exception)) from exception

    async def download_content_range(
        self,
        *,
        url: str,
        start: int,
        end: int,
    ) -> None:
        """Download a specific range of a file's content using a presigned download url."""
        headers = httpx.Headers(
            {
                "Range": f"bytes={start}-{end}",
                "Cache-Control": "no-store",  # don't cache part downloads
            }
        )

        try:
            response: httpx.Response = await retry_handler(
                fn=self._client.get, url=url, headers=headers
            )
        except RetryError as retry_error:
            wrapped_exception = retry_error.last_attempt.exception()

            if isinstance(wrapped_exception, httpx.RequestError):
                exceptions.raise_if_connection_failed(
                    request_error=wrapped_exception, url=url
                )
                raise exceptions.RequestFailedError(url=url) from retry_error
            elif wrapped_exception:
                raise wrapped_exception from retry_error
            elif result := retry_error.last_attempt.result():
                response = result
            else:
                raise

        status_code = response.status_code

        # 200, if the full file was returned, 206 else.
        if status_code in (200, 206):
            await self._queue.put((start, response.content))
            return

        raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

    async def drain_queue_to_file(
        self,
        *,
        file: BufferedWriter,
        file_size: int,
        offset: int,
        progress_bar: ProgressBar,
    ) -> None:
        """Write downloaded file bytes from queue.
        This should be started as asyncio.Task and awaited after the download_to_queue
        tasks have been created/started.
        """
        # track and display actually written bytes
        downloaded_size = 0

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
