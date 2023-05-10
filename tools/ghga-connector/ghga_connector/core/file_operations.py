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

"""
Contains Calls of the Presigned URLs in order to Up- and Download Files
"""

import base64
import concurrent.futures
import math
from io import BufferedReader
from pathlib import Path
from queue import Queue
from tempfile import mkstemp
from typing import Any, Iterator, Sequence, Tuple, Union

import crypt4gh.keys
import crypt4gh.lib
import requests

from ghga_connector.core import exceptions
from ghga_connector.core.constants import TIMEOUT
from ghga_connector.core.session import RequestsSession


class Crypt4GHEncryptor:
    """Convenience class to deal with Crypt4GH encryption"""

    def __init__(
        self,
        server_pubkey: str,
        submitter_private_key_path: Path,
    ) -> None:
        self.server_public = base64.b64decode(server_pubkey)
        self.submitter_private = crypt4gh.keys.get_private_key(
            submitter_private_key_path, callback=None
        )

    def encrypt_file(self, *, file_path: Path) -> Path:
        """Encrypt provided file using Crypt4GH lib"""
        keys = [(0, self.submitter_private, self.server_public)]
        with file_path.open("rb") as infile:
            # NamedTemporaryFile cannot be opened a second time on Windows, manually
            # deal with setup + teardown instead
            raw_fd, outfile_path = mkstemp()
            with open(raw_fd, "wb") as outfile:
                crypt4gh.lib.encrypt(keys=keys, infile=infile, outfile=outfile)
            return Path(outfile_path)


class Crypt4GHDecryptor:
    """Convenience class to deal with Crypt4GH decryption"""

    def __init__(self, decryption_key_path: Path):
        self.decryption_key = crypt4gh.keys.get_private_key(
            decryption_key_path, callback=None
        )

    def decrypt_file(self, *, input_path: Path, output_path: Path):
        """Decrypt provided file using Crypt4GH lib"""
        keys = [(0, self.decryption_key, None)]
        with input_path.open("rb") as infile:
            with output_path.open("wb") as outfile:
                crypt4gh.lib.decrypt(keys=keys, infile=infile, outfile=outfile)


def is_file_encrypted(file_path: Path):
    """Checks if a file is Crypt4GH encrypted"""

    with file_path.open("rb") as input_file:
        num_relevant_bytes = 12
        file_header = input_file.read(num_relevant_bytes)

        magic_number = b"crypt4gh"
        version = b"\x01\x00\x00\x00"

        if file_header != magic_number + version:
            return False

    # If file header is correct, assume file is Crypt4GH encrypted
    return True


def download_content_range(
    *,
    download_url: str,
    start: int,
    end: int,
    queue: Queue,
) -> None:
    """Download a specific range of a file's content using a presigned download url."""

    headers = {"Range": f"bytes={start}-{end}"}
    try:
        response = RequestsSession.get(
            download_url, headers=headers, timeout=TIMEOUT, allow_redirects=False
        )
    except requests.exceptions.RequestException as request_error:
        exceptions.raise_if_max_retries(request_error=request_error, url=download_url)
        raise exceptions.RequestFailedError(url=download_url) from request_error

    status_code = response.status_code

    # 200, if the full file was returned, 206 else.
    if status_code in (200, 206):
        queue.put((start, response.content))
        return

    raise exceptions.BadResponseCodeError(url=download_url, response_code=status_code)


def download_file_parts(
    max_concurrent_downloads: int,
    queue: Queue,
    part_ranges: Sequence[Tuple[int, int]],
    download_urls: Iterator[Union[Tuple[None, None, int], Tuple[str, int, None]]],
    download_part_funct=download_content_range,
) -> None:
    """
    Download stuff
    """
    # Download the parts using a thread pool executor
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=max_concurrent_downloads,
    )

    for part_range, download_url in zip(part_ranges, download_urls):
        kwargs: dict[str, Any] = {
            "download_url": download_url[0],
            "start": part_range[0],
            "end": part_range[1],
            "queue": queue,
        }

        executor.submit(download_part_funct, **kwargs)


def calc_part_ranges(
    *, part_size: int, total_file_size: int, from_part: int = 1
) -> Sequence[tuple[int, int]]:
    """
    Calculate and return the ranges (start, end) of file parts as a list of tuples.

    By default it starts with the first part but you may also start from a specific part
    in the middle of the file using the `from_part` argument. This might be useful to
    resume an interrupted reading process.
    """
    # calc the ranges for the parts that have the full part_size:
    full_part_number = math.floor(total_file_size / part_size)
    part_ranges = [
        (part_size * (part_no - 1), part_size * part_no - 1)
        for part_no in range(from_part, full_part_number + 1)
    ]

    if (total_file_size % part_size) > 0:
        # if the last part is smaller than the part_size, calculate its range separately:
        part_ranges.append((part_size * full_part_number, total_file_size - 1))

    return part_ranges


def read_file_parts(
    file: BufferedReader, *, part_size: int, from_part: int = 1
) -> Iterator[bytes]:
    """
    Returns an iterator to iterate through file parts of the given size (in bytes).

    By default it start with the first part but you may also start from a specific part
    in the middle of the file using the `from_part` argument. This might be useful to
    resume an interrupted reading process.

    Please note: opening and closing of the file MUST happen outside of this function.
    """

    initial_offset = part_size * (from_part - 1)
    file.seek(initial_offset)

    while True:
        file_part = file.read(part_size)

        if len(file_part) == 0:
            return

        yield file_part


def upload_file_part(*, presigned_url: str, part: bytes) -> None:
    """Upload File"""

    try:
        response = RequestsSession.put(presigned_url, data=part, timeout=TIMEOUT)
    except requests.exceptions.RequestException as request_error:
        exceptions.raise_if_max_retries(request_error=request_error, url=presigned_url)
        raise exceptions.RequestFailedError(url=presigned_url) from request_error

    status_code = response.status_code
    if status_code == 200:
        return

    raise exceptions.BadResponseCodeError(url=presigned_url, response_code=status_code)
