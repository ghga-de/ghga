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

"""Unit tests for models"""

from math import ceil

import crypt4gh.lib
import pytest

from tests.fixtures.config import get_config
from tests.fixtures.utils import get_encrypted_object, make_file_upload


def test_file_upload_offset():
    """Test the computed properties of a FileUpload"""
    part_size = 5 * 1024**2
    encrypted_object = get_encrypted_object(part_size=part_size)
    f = make_file_upload(
        encrypted_object.unencrypted_size,
        encrypted_object.encrypted_size,
        part_size=part_size,
    )

    assert f.offset == encrypted_object.offset


def test_calc_part_ranges():
    """Test the calc_encrypted_part_ranges() method"""
    # Test with a file that has multiple parts
    part_size = 5 * 1024**2  # 5 MiB
    file_size = int(part_size * 2.5)  # 2.5 parts worth of data
    encrypted_object = get_encrypted_object(part_size=part_size, file_size=file_size)
    f = make_file_upload(
        encrypted_object.unencrypted_size,
        encrypted_object.encrypted_size,
        part_size=part_size,
    )

    # Calculate the encrypted segment size
    encrypted_segment_size = crypt4gh.lib.CIPHER_SEGMENT_SIZE

    # Calculate the expected adjusted part size
    segments_per_part = ceil(part_size / encrypted_segment_size)
    expected_adjusted_part_size = segments_per_part * encrypted_segment_size

    # Get all part ranges
    ranges = list(f.calc_encrypted_part_ranges())

    # Verify we got the expected number of parts (3 parts for 2.5 parts worth)
    assert len(ranges) == 3, f"Expected 3 parts, got {len(ranges)}"

    # Verify first range starts at the offset (after the envelope)
    assert ranges[0].start == f.offset

    # Verify last range ends at the encrypted size
    assert ranges[-1].stop == encrypted_object.encrypted_size

    # Verify ranges are contiguous (no gaps or overlaps)
    for i in range(len(ranges) - 1):
        assert ranges[i].stop == ranges[i + 1].start

    # Verify all ranges except possibly the last are the expected size
    for r in ranges[:-1]:
        size = r.stop - r.start
        assert size == expected_adjusted_part_size

    # Verify the last part size is <= expected_adjusted_part_size
    last_size = ranges[-1].stop - ranges[-1].start
    assert last_size <= expected_adjusted_part_size

    # Verify total coverage (all ranges cover encrypted_size - offset bytes)
    total_coverage = sum(r.stop - r.start for r in ranges)
    expected_coverage = encrypted_object.encrypted_size - f.offset
    assert total_coverage == expected_coverage


def test_calc_part_ranges_single_part():
    """Test calc_encrypted_part_ranges() with a small file that fits in one part"""
    part_size = 10 * 1024**2  # 10 MiB
    file_size = 1024**2  # 1 MiB (much smaller than part_size)
    encrypted_object = get_encrypted_object(part_size=part_size, file_size=file_size)
    f = make_file_upload(
        encrypted_object.unencrypted_size,
        encrypted_object.encrypted_size,
        part_size=part_size,
    )

    ranges = list(f.calc_encrypted_part_ranges())

    # Should have exactly one part
    assert len(ranges) == 1

    # Should cover the entire encrypted content (minus envelope)
    assert ranges[0].start == f.offset
    assert ranges[0].stop == encrypted_object.encrypted_size


def test_adjusted_part_size_small_file():
    """Test that adjusted part size is calculated so the part size is, except for
    the last part, evenly divisible by CIPHER_SEGMENT_SIZE.
    """
    # Test case A: Normal case - part size is adjusted to align with CIPHER_SEGMENT_SIZE
    part_size = 5 * 1024**2  # 5 MiB
    decrypted_size = 100 * 1024**2  # 100 MiB
    # Calculate approximate encrypted size (slightly larger due to encryption overhead)
    encrypted_size = (
        decrypted_size + (decrypted_size // crypt4gh.lib.SEGMENT_SIZE) * 28 + 1000
    )

    f = make_file_upload(decrypted_size, encrypted_size, part_size=part_size)

    # Verify adjusted part size is evenly divisible by CIPHER_SEGMENT_SIZE
    assert f.adjusted_part_size % crypt4gh.lib.CIPHER_SEGMENT_SIZE == 0

    # Verify all ranges (except possibly the last) use the adjusted part size
    ranges = list(f.calc_encrypted_part_ranges())
    assert ranges.pop().stop == f.encrypted_size
    assert all((r.stop - r.start) == f.adjusted_part_size for r in ranges)


def test_adjusted_part_size_big_file():
    """Test that adjusted part size is calculated so there are less than 10k parts in
    the interrogation bucket upload.
    """
    # Test case B: Large file that would exceed 10k parts with normal part size
    part_size = 5 * 1024**2  # 5 MiB
    # Create a large file: 60 GiB decrypted would result in > 10k parts at 5 MiB each
    decrypted_size = 60 * 1024**3  # 60 GiB
    # Calculate approximate encrypted size
    encrypted_size = (
        decrypted_size + (decrypted_size // crypt4gh.lib.SEGMENT_SIZE) * 28 + 1000
    )

    f_large = make_file_upload(decrypted_size, encrypted_size, part_size=part_size)

    # Verify adjusted part size is still evenly divisible by CIPHER_SEGMENT_SIZE
    assert f_large.adjusted_part_size % crypt4gh.lib.CIPHER_SEGMENT_SIZE == 0

    # Verify that the number of parts is less than 10,000
    ranges_large = list(f_large.calc_encrypted_part_ranges())
    assert len(ranges_large) < 10_000, (
        f"Expected < 10000 parts, got {len(ranges_large)}"
    )

    # Verify the adjusted part size was actually increased from the original
    # Calculate what the non-adjusted aligned part size would be
    segments_per_part = max(1, part_size // crypt4gh.lib.CIPHER_SEGMENT_SIZE)
    basic_adjusted_part_size = segments_per_part * crypt4gh.lib.CIPHER_SEGMENT_SIZE

    # If the file would exceed 10k parts with the basic adjusted size,
    # the adjusted_part_size should be larger
    encrypted_content_size = encrypted_size - f_large.offset
    if ceil(encrypted_content_size / basic_adjusted_part_size) >= 10_000:
        assert f_large.adjusted_part_size > basic_adjusted_part_size


def test_config_validator():
    """Test the validator for client_reraise_from_retry_error"""
    # Error when True:
    with pytest.raises(ValueError):
        _ = get_config(client_reraise_from_retry_error=True)

    # No error when False:
    _ = get_config(client_reraise_from_retry_error=False)
