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
"""Contains general logic that needs to be exposed to higher level core functionality"""

from pathlib import Path
from queue import Empty, Queue

from ghga_connector.core import exceptions
from ghga_connector.core.downloading.abstract_downloader import DownloaderBase
from ghga_connector.core.downloading.progress_bar import ProgressBar
from ghga_connector.core.file_operations import calc_part_ranges
from ghga_connector.core.message_display import AbstractMessageDisplay


def run_download(
    downloader: DownloaderBase,
    max_wait_time: int,
    message_display: AbstractMessageDisplay,
    output_file_ongoing: Path,
    part_size: int,
):
    """Use the provided downloader to run the whole download process."""
    # stage download and get file size
    url_response = downloader.await_download_url(
        max_wait_time=max_wait_time,
        message_display=message_display,
    )

    # get file header envelope
    try:
        envelope = downloader.get_file_header_envelope()
    except (
        exceptions.FileNotRegisteredError,
        exceptions.EnvelopeNotFoundError,
        exceptions.ExternalApiError,
    ) as error:
        raise exceptions.GetEnvelopeError() from error

    # perform the download
    try:
        download_parts(
            downloader=downloader,
            envelope=envelope,
            output_file=output_file_ongoing,
            part_size=part_size,
            file_size=url_response.file_size,
        )
    except (
        exceptions.ConnectionFailedError,
        exceptions.NoS3AccessMethodError,
    ) as error:
        # Remove file if the download failed.
        output_file_ongoing.unlink()
        raise exceptions.DownloadError() from error


def download_parts(  # noqa: PLR0913
    *,
    downloader: DownloaderBase,
    max_concurrent_downloads: int = 5,
    max_queue_size: int = 10,
    part_size: int,
    file_size: int,
    output_file: Path,
    envelope: bytes,
):
    """
    Downloads a file from the given URL using multiple threads and saves it to a file.

    :param max_concurrent_downloads: Maximum number of parallel downloads.
    :param max_queue_size: Maximum size of the queue.
    :param part_size: Size of each part to download.
    """
    # Create a queue object to store downloaded parts
    queue: Queue = Queue(maxsize=max_queue_size)

    # Split the file into parts based on the part size
    part_ranges = calc_part_ranges(part_size=part_size, total_file_size=file_size)

    # Get the download urls
    download_urls = downloader.get_download_urls()

    # Download the file parts in parallel
    downloader.download_file_parts(
        max_concurrent_downloads=max_concurrent_downloads,
        queue=queue,
        part_ranges=part_ranges,
        url_response=download_urls,
    )

    # Write the downloaded parts to a file
    with output_file.open("wb") as file:
        # put envelope in file
        file.write(envelope)
        offset = len(envelope)
        downloaded_size = 0

        # track and display actually written bytes
        with ProgressBar(file_name=output_file.name, file_size=file_size) as progress:
            while downloaded_size < file_size:
                try:
                    # this will block forever, poll instead and retry if empty
                    start, part = queue.get(block=False)
                except Empty:
                    # not sure if this ramps up CPU usage and this should sleep for some
                    # amount of time
                    continue
                file.seek(offset + start)
                file.write(part)
                # update tracking information
                chunk_size = len(part)
                downloaded_size += chunk_size
                queue.task_done()
                progress.advance(chunk_size)
