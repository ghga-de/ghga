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
#
"""Wrapper functionality for checksum generation"""

import hashlib


def md5_hex(data: bytes | bytearray) -> str:
    """Return the MD5 of `data` as a hex digest."""
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def sha256_hex(data: bytes | bytearray) -> str:
    """Return the SHA-256 of `data` as a hex digest."""
    return hashlib.sha256(data).hexdigest()


class Checksums:
    """Container for checksum calculation

    The plaintext SHA-256 grows as the file is read. The hashes of the encrypted parts
    are set per part number, in any order, and read back in part order.
    """

    def __init__(self):
        self.decrypted_sha256 = hashlib.sha256()
        self._parts: dict[int, tuple[str, str]] = {}

    def __str__(self) -> str:
        """Return multiline representation of checksum hashes"""
        return (
            f"Unencrypted: {self.decrypted_sha256.hexdigest()}\n"
            + f"Encrypted MD5: {self.encrypted_parts_md5}\n"
            + f"Encrypted SHA256: {self.encrypted_parts_sha256}"
        )

    def update_decrypted_sha256(self, part: bytes | bytearray | memoryview):
        """Update checksum for unencrypted file"""
        self.decrypted_sha256.update(part)

    def set_part(self, part_number: int, *, md5: str, sha256: str) -> None:
        """Record the MD5 and SHA-256 hex digests of an encrypted part."""
        self._parts[part_number] = (md5, sha256)

    @property
    def part_numbers(self) -> list[int]:
        """The numbers of the parts with hashes, in ascending order."""
        return sorted(self._parts)

    @property
    def encrypted_parts_md5(self) -> list[str]:
        """The MD5 of each encrypted part, in part order."""
        return [self._parts[number][0] for number in self.part_numbers]

    @property
    def encrypted_parts_sha256(self) -> list[str]:
        """The SHA-256 of each encrypted part, in part order."""
        return [self._parts[number][1] for number in self.part_numbers]

    def get_encrypted_checksum_for_s3(self) -> str:
        """Formulate the expected encrypted checksum str (etag) stored by S3."""
        concatenated_md5s = b"".join(
            bytes.fromhex(md5) for md5 in self.encrypted_parts_md5
        )
        object_md5 = hashlib.md5(concatenated_md5s, usedforsecurity=False).hexdigest()
        num_parts = len(self.encrypted_parts_md5)
        return object_md5 + f"-{num_parts}"
