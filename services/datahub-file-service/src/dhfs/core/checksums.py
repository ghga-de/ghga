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

"""Wrapper functionality for checksum generation"""

import hashlib


class Checksums:
    """Container for checksum calculation"""

    def __init__(self):
        self.unencrypted_sha256 = hashlib.sha256()
        self.encrypted_md5: list[bytes] = []
        self.encrypted_sha256: list[bytes] = []

    def __str__(self) -> str:
        """Return multiline representation of checksum hashes"""
        return (
            f"Unencrypted: {self.unencrypted_sha256.hexdigest()}\n"
            + f"Encrypted MD5: {self.encrypted_md5}\n"
            + f"Encrypted SHA256: {self.encrypted_sha256}"
        )

    def encrypted_is_empty(self):
        """Returns true if the encryption checksum buffer is still empty"""
        return not self.encrypted_md5

    def update_unencrypted(self, part: bytes | bytearray | memoryview):
        """Update checksum for unencrypted file"""
        self.unencrypted_sha256.update(part)

    @staticmethod
    def digest_encrypted_part(part: bytes) -> tuple[bytes, bytes]:
        """Return the (md5, sha256) digests of a single encrypted part."""
        return (
            hashlib.md5(part, usedforsecurity=False).digest(),
            hashlib.sha256(part).digest(),
        )

    def update_encrypted(self, part: bytes):
        """Update encrypted part checksums"""
        md5, sha256 = self.digest_encrypted_part(part)
        self.encrypted_md5.append(md5)
        self.encrypted_sha256.append(sha256)

    def set_encrypted_parts(self, digests: list[tuple[bytes, bytes]]):
        """Replace the per-part encrypted checksums; `digests` must be in part order."""
        self.encrypted_md5 = [md5 for md5, _ in digests]
        self.encrypted_sha256 = [sha256 for _, sha256 in digests]

    def encrypted_checksum_for_s3(self) -> str:
        """Formulate the expected encrypted checksum str (etag) stored by S3."""
        concatenated_md5s = b"".join(self.encrypted_md5)
        object_md5 = hashlib.md5(concatenated_md5s, usedforsecurity=False).hexdigest()
        num_parts = len(self.encrypted_md5)
        return f"{object_md5}-{num_parts}"
