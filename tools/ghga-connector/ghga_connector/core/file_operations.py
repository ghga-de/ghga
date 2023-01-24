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

import math
from io import BufferedReader
from typing import Iterator, Sequence

import requests

from ghga_connector.core import exceptions
from ghga_connector.core.constants import TIMEOUT
from ghga_connector.core.session import RequestsSession


def download_content_range(
    *,
    download_url: str,
    start: int,
    end: int,
) -> bytes:
    """Download a specific range of a file's content using a presigned download url."""

    headers = {"Range": f"bytes={start}-{end}"}
    try:
        response = RequestsSession.get(download_url, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.RequestException as request_error:
        exceptions.raise_if_max_retries(request_error=request_error, url=download_url)
        raise exceptions.RequestFailedError(url=download_url) from request_error

    status_code = response.status_code
    # 200, if the full file was returned, 206 else
    if status_code in (200, 206):
        return response.content

    raise exceptions.BadResponseCodeError(url=download_url, response_code=status_code)


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
        # if the last part is smaller than the part_size, calculate it range separately:
        part_ranges.append((part_size * full_part_number, total_file_size - 1))

    return part_ranges


def download_file_parts(
    *,
    download_url: str,
    part_size: int,
    total_file_size: int,
    from_part: int = 1,
    download_range_func=download_content_range,
    calc_ranges_func=calc_part_ranges,
) -> Iterator[bytes]:
    """
    Returns an iterator to obtain the bytes content of a file in a part by part fashion.

    By default it start with the first part but you may also start from a specific part
    in the middle of the file using the `from_part` argument. This might be useful to
    resume an interrupted reading process.
    """

    part_ranges = calc_ranges_func(
        part_size=part_size, total_file_size=total_file_size, from_part=from_part
    )

    for part_start, part_end in part_ranges:
        yield download_range_func(
            download_url=download_url, start=part_start, end=part_end
        )


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
