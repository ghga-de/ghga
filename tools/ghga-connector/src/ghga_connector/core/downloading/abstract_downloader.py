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
"""Contains base class for download functionality"""

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from queue import Queue

from ghga_connector.core.downloading.structs import URLResponse
from ghga_connector.core.message_display import AbstractMessageDisplay
from ghga_connector.core.structs import PartRange


class DownloaderBase(ABC):
    """Base class defining the interface a downloader object needs to provide"""

    @abstractmethod
    def await_download_url(
        self,
        *,
        max_wait_time: int,
        message_display: AbstractMessageDisplay,
    ) -> URLResponse:
        """Wait until download URL can be generated.
        Returns a URLResponse with two attributes:
            1. the download url
            2. the file size in bytes
        """

    @abstractmethod
    def get_download_urls(
        self,
    ) -> Iterator[URLResponse]:
        """For a specific multi-part download, return an iterator to lazily obtain download URLs."""

    @abstractmethod
    def get_file_header_envelope(self) -> bytes:
        """
        Perform a RESTful API call to retrieve a file header envelope.
        Returns:
            The file header envelope (bytes object)
        """

    @abstractmethod
    def download_content_range(
        self,
        *,
        download_url: str,
        start: int,
        end: int,
        queue: Queue,
    ) -> None:
        """Download a specific range of a file's content using a presigned download url."""

    @abstractmethod
    def download_file_parts(
        self,
        *,
        url_response: Iterator[URLResponse],
        max_concurrent_downloads: int,
        part_ranges: Sequence[PartRange],
        queue: Queue,
    ) -> None:
        """Download all file parts specified by part_ranges"""
