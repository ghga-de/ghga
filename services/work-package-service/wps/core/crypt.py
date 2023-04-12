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

"""Helper functions for encryption."""

import base64

from nacl.public import PublicKey, SealedBox

__all__ = ["encrypt", "decode_public_key"]


def decode_public_key(key: str) -> PublicKey:
    """Return the given base64 encoded public key as a PublicKey object.

    Raises a ValueError if the given key is invalid.
    """
    try:
        decoded_key = base64.b64decode(key)
    except base64.binascii.Error as error:  # type: ignore
        raise ValueError(str(error)) from error
    return PublicKey(decoded_key)


def encrypt(data: str, key: str) -> str:
    """Encrypt a str of ASCII characters with a base64 encoded Crypt4GH key.

    The result will be base64 encoded again.
    """
    sealed_box = SealedBox(decode_public_key(key))
    decoded_data = bytes(data, encoding="ascii")
    encrypted = sealed_box.encrypt(decoded_data)
    return base64.b64encode(encrypted).decode("ascii")
