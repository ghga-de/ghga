# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Unit tests for the upload data structures in structs.py"""

from math import ceil
from pathlib import Path

import crypt4gh.lib
import pytest

from ghga_connector.constants import (
    MAX_ALIGNED_PART_SIZE,
    MAX_PART_SIZE,
    MIN_ALIGNED_PART_SIZE,
    MIN_PART_SIZE,
)
from ghga_connector.core.uploading.structs import (
    ENVELOPE_SIZE,
    CoreFileInfo,
    FileInfoForUpload,
)

SEGMENT_SIZE = crypt4gh.lib.SEGMENT_SIZE
CIPHER_SEGMENT_SIZE = crypt4gh.lib.CIPHER_SEGMENT_SIZE


def make_core_file_info(decrypted_size: int) -> CoreFileInfo:
    """Make a CoreFileInfo instance with the given decrypted size"""
    return CoreFileInfo(
        alias="test", path=Path("/dev/null"), decrypted_size=decrypted_size
    )


def make_file_info_for_upload(
    decrypted_size: int, configured_part_size: int
) -> FileInfoForUpload:
    """Make a FileInfoForUpload instance with the given decrypted size and part size"""
    return FileInfoForUpload(
        core_file_info=make_core_file_info(decrypted_size),
        configured_part_size=configured_part_size,
    )


@pytest.mark.parametrize(
    "decrypted_size, expected",
    [
        # Zero-byte file: only the envelope
        (0, ENVELOPE_SIZE),
        # Sub-segment file: remainder gets nonce + auth tag overhead
        (100, 100 + crypt4gh.lib.CIPHER_DIFF + ENVELOPE_SIZE),
        # Exactly one full segment: no remainder chunk
        (SEGMENT_SIZE, CIPHER_SEGMENT_SIZE + ENVELOPE_SIZE),
        # One full segment + 1-byte remainder
        (
            SEGMENT_SIZE + 1,
            CIPHER_SEGMENT_SIZE + 1 + crypt4gh.lib.CIPHER_DIFF + ENVELOPE_SIZE,
        ),
        # Multiple full segments, no remainder
        (3 * SEGMENT_SIZE, 3 * CIPHER_SEGMENT_SIZE + ENVELOPE_SIZE),
        # Multiple segments + remainder
        (
            2 * SEGMENT_SIZE + 500,
            2 * CIPHER_SEGMENT_SIZE + 500 + crypt4gh.lib.CIPHER_DIFF + ENVELOPE_SIZE,
        ),
    ],
)
def test_encrypted_size(decrypted_size: int, expected: int):
    """Make sure that `encrypted_size` is calculated correctly for various file sizes.

    The value includes both the encrypted file content and the Crypt4GH envelope.
    """
    assert make_core_file_info(decrypted_size).encrypted_size == expected


def test_part_size_already_aligned():
    """Make sure that a configured part size already aligned to CIPHER_SEGMENT_SIZE
    at MIN_ALIGNED passes through unchanged.

    MIN_ALIGNED is the smallest multiple of CIPHER_SEGMENT_SIZE that is at least 5 MiB.
    """
    info = make_file_info_for_upload(100, configured_part_size=MIN_ALIGNED_PART_SIZE)
    assert info.part_size == MIN_ALIGNED_PART_SIZE
    assert info.part_size % CIPHER_SEGMENT_SIZE == 0


def test_part_size_rounds_up_to_next_segment():
    """Make sure that a configured part size one byte above an alignment boundary
    is rounded up by exactly one cipher segment.
    """
    info = make_file_info_for_upload(
        100, configured_part_size=MIN_ALIGNED_PART_SIZE + 1
    )
    assert info.part_size == MIN_ALIGNED_PART_SIZE + CIPHER_SEGMENT_SIZE
    assert info.part_size % CIPHER_SEGMENT_SIZE == 0


def test_part_size_clamped_up_to_min():
    """Make sure that a configured part size below the S3 5 MiB minimum is raised to MIN_ALIGNED."""
    info = make_file_info_for_upload(100, configured_part_size=1_000)
    assert info.part_size == MIN_ALIGNED_PART_SIZE
    assert info.part_size >= MIN_PART_SIZE
    assert info.part_size % CIPHER_SEGMENT_SIZE == 0


def test_part_size_clamped_down_to_max():
    """Make sure that a configured part size above the S3 5 GiB maximum is lowered to MAX_ALIGNED."""
    info = make_file_info_for_upload(100, configured_part_size=MAX_PART_SIZE + 1)
    assert info.part_size == MAX_ALIGNED_PART_SIZE
    assert info.part_size <= MAX_PART_SIZE
    assert info.part_size % CIPHER_SEGMENT_SIZE == 0


def test_part_size_adjusted_for_10k_limit():
    """Make sure that the part size is grown for very large files to keep the part count under 10 000."""
    # Build a file large enough that default-sized parts would exceed 10k.
    n_segments = ceil(10_000 * MIN_ALIGNED_PART_SIZE / CIPHER_SEGMENT_SIZE) + 1
    decrypted_size = n_segments * SEGMENT_SIZE  # no remainder == good
    info = make_file_info_for_upload(
        decrypted_size, configured_part_size=CIPHER_SEGMENT_SIZE
    )

    assert info.part_size % CIPHER_SEGMENT_SIZE == 0
    assert info.part_size >= MIN_PART_SIZE
    assert info.part_size <= MAX_PART_SIZE
    assert ceil(info.encrypted_size / info.part_size) < 10_000
