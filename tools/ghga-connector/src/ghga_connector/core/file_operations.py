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

"""Contains calls of the Presigned URLs in order to Up- and Download Files"""

import math
from collections.abc import Generator, Iterator
from io import BufferedReader
from pathlib import Path
from typing import Any

from .structs import PartRange


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


def calc_part_ranges(
    *, part_size: int, total_file_size: int, from_part: int = 1
) -> Generator[PartRange, Any, Any]:
    """
    Calculate and return the ranges (start, end) of file parts as a list of tuples.

    By default it starts with the first part but you may also start from a specific part
    in the middle of the file using the `from_part` argument. This might be useful to
    resume an interrupted reading process.
    """
    # calc the ranges for the parts that have the full part_size:
    full_part_number = math.floor(total_file_size / part_size)
    part_ranges = [
        PartRange(start=part_size * (part_no - 1), stop=part_size * part_no - 1)
        for part_no in range(from_part, full_part_number + 1)
    ]

    if (total_file_size % part_size) > 0:
        # if the last part is smaller than the part_size, calculate its range separately:
        part_ranges.append(
            PartRange(start=part_size * full_part_number, stop=total_file_size - 1)
        )

    yield from part_ranges


def get_segments(part: bytes, segment_size: int):
    """Chunk file part into cipher segments"""
    full_segments = len(part) // segment_size
    segments = [
        part[i * segment_size : (i + 1) * segment_size] for i in range(full_segments)
    ]
    # get potential remainder of bytes that we need to handle
    # for non-matching boundaries between part and cipher segment size
    incomplete_segment = part[full_segments * segment_size :]
    return segments, incomplete_segment


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
