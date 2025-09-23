# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Contains utility functions to deal with Crypt4GH on a slightly higher level."""

from __future__ import annotations

import base64
import io
import os
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from tempfile import mkstemp
from typing import NamedTuple, cast

import crypt4gh.header
import crypt4gh.lib
from crypt4gh.keys import c4gh, get_private_key, get_public_key

from ghga_service_commons.utils.temp_files import big_temp_file

__all__ = [
    "Crypt4GHKeyPair",
    "create_envelope",
    "decrypt_file",
    "extract_file_secret",
    "generate_keypair",
    "random_encrypted_content",
]


class Crypt4GHKeyPair(NamedTuple):
    """Crypt4GH keypair"""

    private: bytes
    public: bytes


class RandomEncryptedData(NamedTuple):
    """Container for random Crypt4GH encrypted data.

    If not used as a context manager, the user has to take care of closing the content object.
    """

    content: io.BytesIO
    decrypted_size: int

    def __enter__(self):
        """Nothing to set up, just return self"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Deal with open resources"""
        self.close()

    def close(self):
        """Close in-memory BytesIO content."""
        self.content.close()


def key_secret_decoder(function: Callable):
    """Decorator decoding string arguments from base64 to bytes"""

    @wraps(function)
    def wrapper(**kwargs):
        """Decode all string keyword arguments from base64 to bytes"""
        for key, value in kwargs.items():
            if isinstance(value, str):
                if key.endswith(("_key", "_secret")) or key.startswith("encrypted"):
                    kwargs[key] = base64.b64decode(value)
                elif key.endswith("_path"):
                    kwargs[key] = Path(value)
        return function(**kwargs)

    return wrapper


@key_secret_decoder
def create_envelope(
    *, file_secret: str | bytes, private_key: str | bytes, public_key: str | bytes
) -> bytes:
    """Create a new Crypt4GH header/envelope.

    Arguments should be passed as base64 encoded string or raw bytes.

    Returns:
        bytes: Crypt4GH envelope containing encrypted symmetric file secret
    """
    keys = [(0, private_key, public_key)]
    header_content = crypt4gh.header.make_packet_data_enc(0, file_secret)
    header_packets = crypt4gh.header.encrypt(header_content, keys)
    return crypt4gh.header.serialize(header_packets)


@key_secret_decoder
def decrypt_file(
    *, input_path: str | Path, output_path: str | Path, private_key: str | bytes
) -> None:
    """Decrypt a Crypt4GH encrypted file.

    Private key should be passed as base64 encoded string or raw bytes.
    """
    keys = [(0, private_key, None)]
    input_path, output_path = cast(tuple[Path, Path], (input_path, output_path))
    with input_path.open("rb") as infile, output_path.open("wb") as outfile:
        crypt4gh.lib.decrypt(keys=keys, infile=infile, outfile=outfile)


@key_secret_decoder
def extract_file_secret(
    *, encrypted_header: str | bytes, private_key: str | bytes, public_key: str | bytes
) -> bytes:
    """Extract symmetric secret from Crypt4GH header/envelope.

    Arguments should be passed as base64 encoded string or raw bytes.

    Returns:
        bytes: symmetric files secret from header.
            Only one secret is supported for now.
    """
    # (method - only 0 supported for now, private_key, public_key)
    keys = [(0, private_key, None)]
    encrypted_header = cast(bytes, encrypted_header)
    infile = io.BytesIO(encrypted_header)
    session_keys, _ = crypt4gh.header.deconstruct(
        infile=infile, keys=keys, sender_pubkey=public_key
    )

    return session_keys[0]


def generate_keypair() -> Crypt4GHKeyPair:
    """Generate a new Crypt4GH keypair."""
    sk_file, sk_path = mkstemp(prefix="private", suffix=".key")
    pk_file, pk_path = mkstemp(prefix="public", suffix=".key")

    # Crypt4GH does not reset the umask it sets, so we need to deal with it
    original_umask = os.umask(0o022)
    passphrase = os.urandom(32).hex().encode()
    c4gh.generate(seckey=sk_file, pubkey=pk_file, passphrase=passphrase)
    public_key = get_public_key(pk_path)
    private_key = get_private_key(sk_path, passphrase.decode)
    os.umask(original_umask)

    Path(pk_path).unlink()
    Path(sk_path).unlink()

    return Crypt4GHKeyPair(private=private_key, public=public_key)


@key_secret_decoder
def random_encrypted_content(
    file_size: int, private_key: str | bytes, public_key: str | bytes
) -> RandomEncryptedData:
    """Create an in-memory file with random content that is Crypt4GH encrypted."""
    encrypted_file = io.BytesIO()

    with big_temp_file(file_size) as raw_file:
        # rewind input file for reading
        true_size = raw_file.tell()
        raw_file.seek(0)
        keys = [(0, private_key, public_key)]
        crypt4gh.lib.encrypt(keys=keys, infile=raw_file, outfile=encrypted_file)

    # rewind output file for reading
    encrypted_file.seek(0)
    return RandomEncryptedData(content=encrypted_file, decrypted_size=true_size)
