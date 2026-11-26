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

from ghga_connector.core.crypt.checksums import Checksums, md5_hex, sha256_hex


def set_parts(checksums: Checksums, parts: dict[int, bytes]) -> None:
    """Record the hashes of the given parts, in the order of the dict."""
    for number, part in parts.items():
        checksums.set_part(number, md5=md5_hex(part), sha256=sha256_hex(part))


def test_hex_helpers_match_hashlib():
    """Make sure the helpers return hashlib's hex digests, also for a bytearray."""
    part = bytearray(b"encrypted block")
    assert md5_hex(part) == hashlib.md5(part, usedforsecurity=False).hexdigest()
    assert sha256_hex(part) == hashlib.sha256(part).hexdigest()


def test_set_part_out_of_order_reads_in_part_order():
    """Make sure part hashes set out of order come back in part order."""
    parts = {3: b"part three", 1: b"part one", 2: b"part two"}
    checksums = Checksums()
    set_parts(checksums, parts)

    assert checksums.part_numbers == [1, 2, 3]
    assert checksums.encrypted_parts_md5 == [md5_hex(parts[n]) for n in (1, 2, 3)]
    assert checksums.encrypted_parts_sha256 == [sha256_hex(parts[n]) for n in (1, 2, 3)]


def test_encrypted_checksum_for_s3_single_part():
    """Make sure encrypted_checksum_for_s3() works for a single part."""
    checksums = Checksums()
    part = b"some encrypted data"
    set_parts(checksums, {1: part})

    md5_hex_digest = hashlib.md5(part, usedforsecurity=False).hexdigest()
    # S3 ETag: MD5 of concatenated raw MD5s, hyphen, part count
    expected_etag = (
        hashlib.md5(bytes.fromhex(md5_hex_digest), usedforsecurity=False).hexdigest()
        + "-1"
    )
    assert checksums.get_encrypted_checksum_for_s3() == expected_etag


def test_encrypted_checksum_for_s3_multiple_parts():
    """Make sure encrypted_checksum_for_s3() follows the part order, not the order in
    which the parts were set.
    """
    checksums = Checksums()
    parts = [b"part one", b"part two", b"part three"]
    set_parts(checksums, {3: parts[2], 1: parts[0], 2: parts[1]})

    md5_hexes = [hashlib.md5(p, usedforsecurity=False).hexdigest() for p in parts]
    concat = b"".join(bytes.fromhex(h) for h in md5_hexes)
    expected_etag = (
        hashlib.md5(concat, usedforsecurity=False).hexdigest() + f"-{len(parts)}"
    )
    assert checksums.get_encrypted_checksum_for_s3() == expected_etag
