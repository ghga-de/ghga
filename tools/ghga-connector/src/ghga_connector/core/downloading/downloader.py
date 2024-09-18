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

import base64
from asyncio import Queue, Semaphore, Task, create_task
from collections.abc import Coroutine
from io import BufferedWriter
from pathlib import Path
from time import sleep
from typing import Any, Union

import httpx
from tenacity import RetryError

from ghga_connector.core import (
    AbstractMessageDisplay,
    HttpxClientConfigurator,
    PartRange,
    ResponseExceptionTranslator,
    WorkPackageAccessor,
    calc_part_ranges,
    exceptions,
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

    async def schedule(self, fn: Coroutine[Any, Any, None]):
        """Create a task and register its callback."""
        task = create_task(fn)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


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
        self._queue: Queue[Union[tuple[int, bytes], BaseException]] = Queue()
        self._semaphore = Semaphore(value=max_concurrent_downloads)
        self._retry_handler = HttpxClientConfigurator.retry_handler

    async def download_file(self, *, output_path: Path, part_size: int):
        """Download file to the specified location and manage lower level details."""
        # stage download and get file size
        url_response = await self.await_download_url()

        # Split the file into parts based on the part size
        part_ranges = calc_part_ranges(
            part_size=part_size, total_file_size=url_response.file_size
        )

        task_handler = TaskHandler()

        # start async part download to intermediate queue
        for part_range in part_ranges:
            await task_handler.schedule(self.download_to_queue(part_range=part_range))

        # get file header envelope
        try:
            envelope = await self.get_file_header_envelope()
        except (
            exceptions.FileNotRegisteredError,
            exceptions.EnvelopeNotFoundError,
            exceptions.ExternalApiError,
        ) as error:
            raise exceptions.GetEnvelopeError() from error

        # Write the downloaded parts to a file
        with output_path.open("wb") as file:
            # put envelope in file
            file.write(envelope)
            # start download task
            write_to_file = Task(
                self.drain_queue_to_file(
                    file_name=file.name,
                    file=file,
                    file_size=url_response.file_size,
                    offset=len(envelope),
                ),
                name="Write queue to file",
            )
            await write_to_file

    async def await_download_url(self) -> URLResponse:
        """Wait until download URL can be generated.
        Returns a URLResponse containing two elements:
            1. the download url
            2. the file size in bytes
        """
        # get the download_url, wait if needed
        wait_time = 0
        while wait_time < self._max_wait_time:
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
                    "The request was invalid and returned a bad HTTP status code."
                )
                raise error
            except exceptions.RequestFailedError as error:
                self._message_display.failure("The request failed.")
                raise error

            if isinstance(response, RetryResponse):
                retry_time = response.retry_after
                wait_time += retry_time
                self._message_display.display(
                    f"File staging, will try to download again in {retry_time} seconds"
                )
                sleep(retry_time)
            else:
                return response

        raise exceptions.MaxWaitTimeExceededError(max_wait_time=self._max_wait_time)

    async def get_download_url(self) -> URLResponse:
        """Fetch a presigned URL from which file data can be downloaded."""
        url_and_headers = await get_file_authorization(
            file_id=self._file_id, work_package_accessor=self._work_package_accessor
        )
        url_response = await get_download_url(
            client=self._client, url_and_headers=url_and_headers
        )
        if isinstance(url_response, RetryResponse):
            # File should be staged at that point in time
            raise exceptions.UnexpectedRetryResponseError()
        return url_response

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
            try:
                await self.download_content_range(
                    start=part_range.start, end=part_range.stop
                )
            except BaseException as exception:
                await self._queue.put(exception)

    async def download_content_range(
        self,
        *,
        start: int,
        end: int,
    ) -> None:
        """Download a specific range of a file's content using a presigned download url."""
        headers = httpx.Headers({"Range": f"bytes={start}-{end}"})

        url_response = await self.get_download_url()
        download_url = url_response.download_url
        try:
            response: httpx.Response = await self._retry_handler(
                fn=self._client.get, url=download_url, headers=headers
            )
        except RetryError as retry_error:
            wrapped_exception = retry_error.last_attempt.exception()

            if isinstance(wrapped_exception, httpx.RequestError):
                exceptions.raise_if_connection_failed(
                    request_error=wrapped_exception, url=download_url
                )
                raise exceptions.RequestFailedError(url=download_url) from retry_error
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

        raise exceptions.BadResponseCodeError(
            url=download_url, response_code=status_code
        )

    async def drain_queue_to_file(
        self, *, file_name: str, file: BufferedWriter, file_size: int, offset: int
    ) -> None:
        """Write downloaded file bytes from queue.
        This should be started as asyncio.Task and awaited after the download_to_queue
        tasks have been created/started.
        """
        # track and display actually written bytes
        downloaded_size = 0

        with ProgressBar(file_name=file_name, file_size=file_size) as progress:
            while downloaded_size < file_size:
                result = await self._queue.get()
                if isinstance(result, BaseException):
                    raise exceptions.DownloadError(reason=str(result))
                else:
                    start, part = result
                file.seek(offset + start)
                file.write(part)
                # update tracking information
                chunk_size = len(part)
                downloaded_size += chunk_size
                self._queue.task_done()
                progress.advance(chunk_size)
