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
"""This module contains Crypt4GH based encryption functionality"""

import base64
import os
from collections.abc import Generator
from io import BufferedReader
from pathlib import Path
from typing import Union

import crypt4gh.header
import crypt4gh.keys
import crypt4gh.lib
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_encrypt

from ghga_connector.core import get_segments, read_file_parts

from .abstract_bases import Encryptor
from .checksums import Checksums


class Crypt4GHEncryptor(Encryptor):
    """Handles on the fly encryption and checksum calculation"""

    def __init__(
        self,
        part_size: int,
        private_key_path: Path,
        server_public_key: str,
        checksums: Checksums = Checksums(),
        file_secret: Union[bytes, None] = None,
    ):
        self._encrypted_file_size = 0
        self._checksums = checksums
        self._part_size = part_size
        self._private_key_path = private_key_path
        self._server_public_key = base64.b64decode(server_public_key)
        if file_secret is None:
            file_secret = os.urandom(32)
        self._file_secret = file_secret

    def _encrypt(self, part: bytes):
        """Encrypt file part using secret"""
        segments, incomplete_segment = get_segments(
            part=part, segment_size=crypt4gh.lib.SEGMENT_SIZE
        )

        encrypted_segments = [self._encrypt_segment(segment) for segment in segments]

        return b"".join(encrypted_segments), incomplete_segment

    def _encrypt_segment(self, segment: bytes):
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
        private_key = crypt4gh.keys.get_private_key(
            self._private_key_path, callback=None
        )
        keys = [(0, private_key, self._server_public_key)]
        header_content = crypt4gh.header.make_packet_data_enc(0, self._file_secret)
        header_packets = crypt4gh.header.encrypt(header_content, keys)
        header_bytes = crypt4gh.header.serialize(header_packets)

        return header_bytes

    def get_encrypted_size(self) -> int:
        """Get file size after encryption, excluding envelope"""
        return self._encrypted_file_size

    def process_file(self, file: BufferedReader) -> Generator[bytes, None, None]:
        """Encrypt file parts and prepare for upload."""
        unprocessed_bytes = b""
        upload_buffer = self._create_envelope()
        update_encrypted = self._checksums.update_encrypted

        # get envelope size to adjust checksum buffers and encrypted content size
        envelope_size = len(upload_buffer)

        for file_part in read_file_parts(file=file, part_size=self._part_size):
            # process unencrypted
            self._checksums.update_unencrypted(file_part)
            unprocessed_bytes += file_part

            # encrypt in chunks
            encrypted_bytes, unprocessed_bytes = self._encrypt(unprocessed_bytes)
            upload_buffer += encrypted_bytes

            # update checksums and yield if part size
            if len(upload_buffer) >= self._part_size:
                current_part = upload_buffer[: self._part_size]
                if self._checksums.encrypted_is_empty():
                    update_encrypted(current_part[envelope_size:])
                else:
                    update_encrypted(current_part)
                self._encrypted_file_size += self._part_size
                yield current_part
                upload_buffer = upload_buffer[self._part_size :]

        # process dangling bytes
        if unprocessed_bytes:
            upload_buffer += self._encrypt_segment(unprocessed_bytes)

        while len(upload_buffer) >= self._part_size:
            current_part = upload_buffer[: self._part_size]
            update_encrypted(current_part)
            self._encrypted_file_size += self._part_size
            yield current_part
            upload_buffer = upload_buffer[self._part_size :]

        if upload_buffer:
            update_encrypted(upload_buffer)
            self._encrypted_file_size += len(upload_buffer)
            yield upload_buffer

        self._encrypted_file_size -= envelope_size
