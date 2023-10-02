# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Helper functions for Crypt4GH compliant encryption."""

import base64
from typing import NamedTuple, Union

from nacl.public import PrivateKey, PublicKey, SealedBox

__all__ = [
    "generate_key_pair",
    "encode_key",
    "decode_key",
    "decrypt",
    "encrypt",
    "KeyPair",
]


class KeyPair(NamedTuple):
    """A Curve25519 key pair as used in Crypt4GH."""

    private: bytes
    public: bytes


def generate_key_pair() -> KeyPair:
    """Generate a Curve25519 key pair as used in Crypt4GH."""
    keys = PrivateKey.generate()
    return KeyPair(bytes(keys), bytes(keys.public_key))


def encode_key(key: bytes) -> str:
    """Base64 encode a private or public key.

    Note that the private and public keys we use have the same size,
    so the same function with the same check can be used for both.

    Raises ValueError if it is not a bytes string or has a wrong size.
    """
    if not isinstance(key, bytes) or len(key) != PublicKey.SIZE:
        raise ValueError("Invalid key")
    return base64.b64encode(key).decode("ascii")


def decode_key(key: str) -> bytes:
    """Base64 decode a private or public key.

    Note that the private and public keys we use have the same size,
    so the same function with the same check can be used for both.

    Raises ValueError if it is not a base64 encoded string or has a wrong size.
    """
    try:
        decoded_key = base64.b64decode(key)
    except base64.binascii.Error as error:  # type: ignore
        raise ValueError(str(error)) from error
    if len(decoded_key) != PublicKey.SIZE:
        raise ValueError("Invalid key")
    return decoded_key


def decrypt(
    data: Union[bytes, str], key: Union[bytes, str, PrivateKey], encoding: str = "utf-8"
) -> str:
    """Decrypt a base64 encoded or bytes string using a private Crypt4GH key.

    The result will be decoded as a native string using the given encoding.

    Raises a ValueError if the given key cannot be used for decryption.
    """
    if isinstance(key, str):
        key = decode_key(key)
    if isinstance(key, bytes):
        key = PrivateKey(key)
    if not isinstance(key, PrivateKey):
        raise ValueError("Invalid key")
    sealed_box = SealedBox(key)
    if isinstance(data, str):
        data = base64.b64decode(data)
    decrypted_data = sealed_box.decrypt(data)
    return decrypted_data.decode(encoding)


def encrypt(
    data: str, key: Union[bytes, str, PrivateKey, PublicKey], encoding: str = "utf-8"
) -> str:
    """Encrypt a str with given encoding using a public Crypt4GH key.

    The result will be returned as a base64 encoded string.

    Raises a ValueError if the given key cannot be used for encryption.

    A PrivateKey object can be passed as key as well, then the derived public key
    will be used for the encryption.
    """
    if isinstance(key, str):
        key = decode_key(key)
    if isinstance(key, bytes):
        key = PublicKey(key)
    if isinstance(key, PrivateKey):
        key = key.public_key
    if not isinstance(key, PublicKey):
        raise ValueError("Invalid key")
    sealed_box = SealedBox(key)
    decoded_data = bytes(data, encoding=encoding)
    encrypted_data = sealed_box.encrypt(decoded_data)
    return base64.b64encode(encrypted_data).decode("ascii")
