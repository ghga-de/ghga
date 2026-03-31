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
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_encrypt
from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.config import get_crypt4gh_public_key
from ghga_connector.constants import ENVELOPE_SIZE
from ghga_connector.core.crypt.checksums import Checksums
from ghga_connector.core.file_operations import get_segments, read_file_parts

FileProcessor = Generator[tuple[int, bytes], Any, None]


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
        num_segments = math.ceil(file_size / crypt4gh.lib.SEGMENT_SIZE)

        # Expected ciphertext size is used to verify the final object size
        self.expected_ciphertext_size = file_size + num_segments * 28 + ENVELOPE_SIZE

        # Decode the Data Hub public key
        self._data_hub_public_key = base64.b64decode(
            get_crypt4gh_public_key(storage_alias)
        )

    def _encrypt(self, part: bytes):
        """Encrypt file part using secret"""
        segments, incomplete_segment = get_segments(
            part=part, segment_size=crypt4gh.lib.SEGMENT_SIZE
        )
        encrypted_segments = [self._encrypt_segment(segment) for segment in segments]
        return b"".join(encrypted_segments), incomplete_segment

    def _encrypt_segment(self, segment: bytes) -> bytes:
        """Encrypt one single segment"""
        nonce = os.urandom(12)
        encrypted_data = crypto_aead_chacha20poly1305_ietf_encrypt(
            segment, None, nonce, self._file_secret
        )  # no aad
        return nonce + encrypted_data

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

    def _get_current_part_and_update_checksum(self, *, upload_buffer: bytes) -> bytes:
        """Get the next encrypted chunk and update the encrypted checksum and size"""
        # Cap the yielded chunk size at the part size
        current_part = upload_buffer[: self._part_size]
        self.checksums.update_encrypted(current_part)
        self._ciphertext_size += len(current_part)
        return current_part

    def process_file(self, *, file: BufferedReader) -> FileProcessor:
        """Encrypt file parts for upload, yielding a tuple of the part number and content."""
        # Create an upload buffer initialized with the file envelope.
        upload_buffer = self._create_envelope()

        # Create a separate buffer for content that has yet to be encrypted
        unprocessed_bytes = b""
        for part_number, file_part in enumerate(
            read_file_parts(file=file, part_size=self._part_size), start=1
        ):
            # Update the unencrypted content's checksum
            self.checksums.update_decrypted_sha256(file_part)

            # Add the file part to the unencrypted buffer
            unprocessed_bytes += file_part

            # Encrypt the buffer and keep any stragglers in `unprocessed_bytes`
            encrypted_bytes, unprocessed_bytes = self._encrypt(unprocessed_bytes)

            # Add the encrypted bytes to the upload buffer (notice we have two buffers)
            upload_buffer += encrypted_bytes

            # See if having added the file part met the predetermined part size
            if len(upload_buffer) >= self._part_size:
                current_part = self._get_current_part_and_update_checksum(
                    upload_buffer=upload_buffer,
                )
                yield part_number, current_part

                # Trim the yielded/uploaded part from the front of the upload buffer
                upload_buffer = upload_buffer[self._part_size :]

        # All file parts should have been yielded, so process any dangling bytes
        if unprocessed_bytes:
            upload_buffer += self._encrypt_segment(unprocessed_bytes)

        # Remaining bytes could potentially constitute multiple parts, allowing for
        #  corner case where encryption causes remaining bytes to exceed one full part
        while len(upload_buffer) >= self._part_size:
            current_part = self._get_current_part_and_update_checksum(
                upload_buffer=upload_buffer,
            )
            part_number += 1  # manually increment part number now
            yield part_number, current_part
            upload_buffer = upload_buffer[self._part_size :]

        # Now anything left in upload buffer is less than full part size. Yield it too.
        if upload_buffer:
            current_part = self._get_current_part_and_update_checksum(
                upload_buffer=upload_buffer,
            )
            part_number += 1
            yield part_number, upload_buffer

        # Finally, verify the encrypted size and raise an error if it doesn't match.
        if self._ciphertext_size != self.expected_ciphertext_size:
            raise exceptions.CiphertextSizeMismatch(
                actual_ciphertext_size=self._ciphertext_size,
                expected_ciphertext_size=self.expected_ciphertext_size,
            )
