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

from nacl.public import PrivateKey, PublicKey, SealedBox


def encrypt(data: str, key: bytes) -> str:
    """
    Encrypt a str of ASCII characters with a base64 encoded Crypt4GH key.

    The result will be base64 encoded again.
    """
    sealed_box = SealedBox(PublicKey(key))
    decoded_data = bytes(data, encoding="utf-8")
    encrypted = sealed_box.encrypt(decoded_data)

    return base64.b64encode(encrypted).decode("utf-8")


def decrypt(data: str, key: bytes) -> str:
    """
    Decrypt a str of ASCII characters with a base64 encoded Crypt4GH key.

    The result will be base64 encoded again.
    """

    unseal_box = SealedBox(PrivateKey(key))
    encoded_data = base64.b64decode(data)
    decrytped = unseal_box.decrypt(encoded_data)

    return base64.b64encode(decrytped).decode("utf-8")
