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

"""Unit tests for the Checksums class"""

import hashlib

from ghga_connector.core.crypt.checksums import Checksums


def test_update_encrypted_appends_per_part_call():
    """Make sure update_encrypted() appends exactly one MD5 and one SHA256 entry per call."""
    checksums = Checksums()
    part = b"encrypted block"
    checksums.update_encrypted(part)

    assert len(checksums.encrypted_parts_md5) == 1
    assert len(checksums.encrypted_parts_sha256) == 1
    assert (
        checksums.encrypted_parts_md5[0]
        == hashlib.md5(part, usedforsecurity=False).hexdigest()
    )
    assert checksums.encrypted_parts_sha256[0] == hashlib.sha256(part).hexdigest()


def test_encrypted_checksum_for_s3_single_part():
    """Make sure encrypted_checksum_for_s3() works for a single part."""
    checksums = Checksums()
    part = b"some encrypted data"
    checksums.update_encrypted(part)

    md5_hex = hashlib.md5(part, usedforsecurity=False).hexdigest()
    # S3 ETag: MD5 of concatenated raw MD5s, hyphen, part count
    expected_etag = (
        hashlib.md5(bytes.fromhex(md5_hex), usedforsecurity=False).hexdigest() + "-1"
    )
    assert checksums.get_encrypted_checksum_for_s3() == expected_etag


def test_encrypted_checksum_for_s3_multiple_parts():
    """Make sure encrypted_checksum_for_s3() works for multiple parts."""
    checksums = Checksums()
    parts = [b"part one", b"part two", b"part three"]
    for part in parts:
        checksums.update_encrypted(part)

    md5_hexes = [hashlib.md5(p, usedforsecurity=False).hexdigest() for p in parts]
    concat = b"".join(bytes.fromhex(h) for h in md5_hexes)
    expected_etag = (
        hashlib.md5(concat, usedforsecurity=False).hexdigest() + f"-{len(parts)}"
    )
    assert checksums.get_encrypted_checksum_for_s3() == expected_etag
