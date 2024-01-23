# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
import concurrent.futures
from collections.abc import Iterator, Sequence
from queue import Queue
from time import sleep
from typing import Any

import httpx

from ghga_connector.core import exceptions
from ghga_connector.core.api_calls import WorkPackageAccessor
from ghga_connector.core.constants import TIMEOUT
from ghga_connector.core.downloading.abstract_downloader import DownloaderBase
from ghga_connector.core.downloading.api_calls import (
    get_download_url,
    get_envelope_authorization,
    get_file_authorization,
)
from ghga_connector.core.downloading.structs import (
    RetryResponse,
    URLResponse,
)
from ghga_connector.core.http_translation import ResponseExceptionTranslator
from ghga_connector.core.message_display import AbstractMessageDisplay
from ghga_connector.core.structs import PartRange


class Downloader(DownloaderBase):
    """Groups download functionality together that is used in the higher level core modules"""

    def __init__(
        self,
        *,
        file_id: str,
        work_package_accessor: WorkPackageAccessor,
        client: httpx.Client,
    ):
        self._client = client
        self._file_id = file_id
        self._work_package_accessor = work_package_accessor

    def await_download_url(
        self,
        *,
        max_wait_time: int,
        message_display: AbstractMessageDisplay,
    ) -> URLResponse:
        """Wait until download URL can be generated.
        Returns a URLResponse containing two elements:
            1. the download url
            2. the file size in bytes
        """
        # get the download_url, wait if needed
        wait_time = 0
        while wait_time < max_wait_time:
            try:
                url_and_headers = get_file_authorization(
                    file_id=self._file_id,
                    work_package_accessor=self._work_package_accessor,
                )
                response = get_download_url(
                    client=self._client, url_and_headers=url_and_headers
                )
            except exceptions.BadResponseCodeError as error:
                message_display.failure(
                    "The request was invalid and returned a bad HTTP status code."
                )
                raise error
            except exceptions.RequestFailedError as error:
                message_display.failure("The request failed.")
                raise error

            if isinstance(response, RetryResponse):
                retry_time = response.retry_after
                wait_time += retry_time
                message_display.display(
                    f"File staging, will try to download again in {retry_time} seconds"
                )
                sleep(retry_time)
            else:
                return response

        raise exceptions.MaxWaitTimeExceededError(max_wait_time=max_wait_time)

    def get_download_urls(self) -> Iterator[URLResponse]:
        """
        For a specific multi-part download identified by `file_id`, return an iterator to
        lazily obtain download URLs.
        """
        while True:
            url_and_headers = get_file_authorization(
                file_id=self._file_id, work_package_accessor=self._work_package_accessor
            )
            url_response = get_download_url(
                client=self._client, url_and_headers=url_and_headers
            )
            if isinstance(url_response, RetryResponse):
                # File should be staged at that point in time
                raise exceptions.UnexpectedRetryResponseError()
            yield url_response

    def download_content_range(
        self,
        *,
        download_url: str,
        start: int,
        end: int,
        queue: Queue,
    ) -> None:
        """Download a specific range of a file's content using a presigned download url."""
        headers = {"Range": f"bytes={start}-{end}"}
        try:
            response = self._client.get(download_url, headers=headers, timeout=TIMEOUT)
        except httpx.RequestError as request_error:
            exceptions.raise_if_connection_failed(
                request_error=request_error, url=download_url
            )
            raise exceptions.RequestFailedError(url=download_url) from request_error

        status_code = response.status_code

        # 200, if the full file was returned, 206 else.
        if status_code in (200, 206):
            queue.put((start, response.content))
            return

        raise exceptions.BadResponseCodeError(
            url=download_url, response_code=status_code
        )

    def download_file_parts(
        self,
        *,
        url_response: Iterator[URLResponse],
        max_concurrent_downloads: int,
        part_ranges: Sequence[PartRange],
        queue: Queue[tuple[int, bytes]],
    ) -> None:
        """Download all file parts specified by part_ranges"""
        # Download the parts using a thread pool executor
        executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent_downloads,
        )

        for part_range, download_url in zip(part_ranges, url_response):
            kwargs: dict[str, Any] = {
                "download_url": download_url.download_url,
                "start": part_range.start,
                "end": part_range.stop,
                "queue": queue,
            }

            executor.submit(self.download_content_range, **kwargs)

    def get_file_header_envelope(self) -> bytes:
        """
        Perform a RESTful API call to retrieve a file header envelope.
        Returns:
            The file header envelope (bytes object)
        """
        url_and_headers = get_envelope_authorization(
            file_id=self._file_id, work_package_accessor=self._work_package_accessor
        )
        url = url_and_headers.endpoint_url
        # Make function call to get download url
        try:
            response = self._client.get(
                url=url, headers=url_and_headers.headers, timeout=TIMEOUT
            )
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
