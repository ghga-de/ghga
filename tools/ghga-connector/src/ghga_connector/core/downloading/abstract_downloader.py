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
"""Contains base class for download functionality"""

from abc import ABC, abstractmethod
from collections.abc import Coroutine
from io import BufferedWriter
from pathlib import Path
from typing import Any

from ghga_connector.core import PartRange
from ghga_connector.core.downloading.progress_bar import ProgressBar

from .structs import URLResponse


class DownloaderBase(ABC):
    """Base class defining the interface a downloader object needs to provide."""

    @abstractmethod
    def download_file(self, *, output_path: Path, part_size: int):
        """Download file to the specified location and manage lower level details."""

    @abstractmethod
    def fetch_download_url(self) -> Coroutine[URLResponse, Any, Any]:
        """Wait until download URL can be generated.
        Returns a URLResponse containing two elements:
            1. the download url
            2. the file size in bytes
        """

    @abstractmethod
    def get_file_header_envelope(self) -> Coroutine[bytes, Any, Any]:
        """
        Perform a RESTful API call to retrieve a file header envelope.
        Returns:
            The file header envelope (bytes object)
        """

    @abstractmethod
    async def download_to_queue(self, *, part_range: PartRange) -> None:
        """
        Start downloading file parts in parallel into a queue.
        This should be wrapped into asyncio.task and is guarded by a semaphore to limit
        the amount of ongoing parallel downloads to max_concurrent_downloads.
        """

    @abstractmethod
    async def download_content_range(
        self,
        *,
        url: str,
        start: int,
        end: int,
    ) -> None:
        """Download a specific range of a file's content using a presigned url."""

    @abstractmethod
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
