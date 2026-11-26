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
"""Functionality to encrypt files in chunks with Crypt4GH before upload."""

import base64
import math
import os
from collections.abc import Generator
from io import BufferedReader
from typing import Any

import crypt4gh.header
import crypt4gh.lib
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.config import get_crypt4gh_public_key
from ghga_connector.constants import ENVELOPE_SIZE
from ghga_connector.core.crypt.checksums import Checksums

FileProcessor = Generator[tuple[int, bytearray], Any, None]

SEGMENT_SIZE = crypt4gh.lib.SEGMENT_SIZE
# Each encrypted segment carries its nonce in front and its MAC behind
NONCE_SIZE = 12
SEGMENT_OVERHEAD = crypt4gh.lib.CIPHER_DIFF
# How much plaintext is read at a time: whole segments, so that only the file's last
#  segment can be short
READ_SEGMENTS = 64


def _read_full(file: BufferedReader, buffer: memoryview) -> int:
    """Read into `buffer` until it is full or the file ends, and return the byte count.

    A single `readinto` may return less than asked before the end of the file, which
    would end a segment early.
    """
    filled = 0
    while filled < len(buffer):
        count = file.readinto(buffer[filled:])
        if not count:
            break
        filled += count
    return filled


class Crypt4GHEncryptor:
    """Handles on the fly encryption and checksum calculation"""

    def __init__(
        self,
        part_size: int,
        my_private_key: SecretBytes,
        file_size: int,
        storage_alias: str,
    ):
        self._part_size = part_size
        self._my_private_key = my_private_key
        self._file_secret = os.urandom(32)
        self.checksums = Checksums()  # Updated as encryption takes place
        self._ciphertext_size = 0  # Updated as encryption takes place
        num_segments = math.ceil(file_size / SEGMENT_SIZE)

        # Expected ciphertext size is used to verify the final object size
        self.expected_ciphertext_size = (
            file_size + num_segments * SEGMENT_OVERHEAD + ENVELOPE_SIZE
        )

        # Decode the Data Hub public key
        self._data_hub_public_key = base64.b64decode(
            get_crypt4gh_public_key(storage_alias)
        )

    def _create_envelope(self) -> bytes:
        """
        Gather file encryption/decryption secret and assemble a crypt4gh envelope using the
        server's private and the client's public key
        """
        keys = [(0, self._my_private_key.get_secret_value(), self._data_hub_public_key)]
        header_content = crypt4gh.header.make_packet_data_enc(0, self._file_secret)
        header_packets = crypt4gh.header.encrypt(header_content, keys)
        header_bytes = crypt4gh.header.serialize(header_packets)
        return header_bytes

    def get_ciphertext_size(self) -> int:
        """Get the size of the entire encrypted object (content + envelope)."""
        return self._ciphertext_size

    def _finish_part(self, part: bytearray) -> bytearray:
        """Count a finished part toward the ciphertext size, and return it.

        Its hashes are left to the upload, so that they do not hold up the encryption.
        """
        self._ciphertext_size += len(part)
        return part

    def process_file(self, *, file: BufferedReader) -> FileProcessor:
        """Encrypt the file part by part, yielding each part's number and content.

        The plaintext is read a few MiB at a time into one reused buffer, and each
        segment is encrypted straight into the current part behind its nonce. Only a
        segment that crosses the end of a part goes through a scratch buffer, to be
        split between that part and the next. The envelope opens the first part.
        """
        part_size = self._part_size
        cipher = ChaCha20Poly1305(self._file_secret)
        plain = memoryview(bytearray(READ_SEGMENTS * SEGMENT_SIZE))
        scratch = memoryview(bytearray(SEGMENT_SIZE + SEGMENT_OVERHEAD))

        part = bytearray(part_size)
        view = memoryview(part)
        envelope = self._create_envelope()
        view[: len(envelope)] = envelope
        pos = len(envelope)
        # S3 part numbers must be sequential, starting at 1
        part_number = 0

        while read := _read_full(file, plain):
            self.checksums.update_decrypted_sha256(plain[:read])
            segment_count = math.ceil(read / SEGMENT_SIZE)
            nonces = os.urandom(NONCE_SIZE * segment_count)
            for index in range(segment_count):
                start = index * SEGMENT_SIZE
                segment = plain[start : min(start + SEGMENT_SIZE, read)]
                size = len(segment) + SEGMENT_OVERHEAD
                nonce = nonces[index * NONCE_SIZE : (index + 1) * NONCE_SIZE]
                if part_size - pos >= size:
                    view[pos : pos + NONCE_SIZE] = nonce
                    cipher.encrypt_into(
                        nonce, segment, None, view[pos + NONCE_SIZE : pos + size]
                    )
                    pos += size
                else:
                    # The segment crosses the end of the part: split it
                    scratch[:NONCE_SIZE] = nonce
                    cipher.encrypt_into(nonce, segment, None, scratch[NONCE_SIZE:size])
                    head = part_size - pos
                    view[pos:] = scratch[:head]
                    view.release()
                    part_number += 1
                    yield part_number, self._finish_part(part)
                    part = bytearray(part_size)
                    view = memoryview(part)
                    pos = size - head
                    view[:pos] = scratch[head:size]
                if pos == part_size:
                    view.release()
                    part_number += 1
                    yield part_number, self._finish_part(part)
                    part = bytearray(part_size)
                    view = memoryview(part)
                    pos = 0

        # The last part holds what is left, if anything
        view.release()
        if pos:
            del part[pos:]
            part_number += 1
            yield part_number, self._finish_part(part)

        # Finally, verify the encrypted size and raise an error if it doesn't match.
        if self._ciphertext_size != self.expected_ciphertext_size:
            raise exceptions.CiphertextSizeMismatch(
                actual_ciphertext_size=self._ciphertext_size,
                expected_ciphertext_size=self.expected_ciphertext_size,
            )
