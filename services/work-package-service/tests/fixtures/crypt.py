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

import base64

from nacl.public import PrivateKey, SealedBox

__all__ = ["user_crypt4gh_key_pair", "user_public_crypt4gh_key"]

user_crypt4gh_key_pair = PrivateKey.generate()

user_public_crypt4gh_key = base64.b64encode(
    bytes(user_crypt4gh_key_pair.public_key)
).decode("ascii")


def decrypt(encrypted_data: str) -> str:
    """Decrypt a str of base64 encoded ASCII data."""
    unseal_box = SealedBox(user_crypt4gh_key_pair)
    encrypted_bytes = base64.b64decode(encrypted_data)
    decrypted_bytes = unseal_box.decrypt(encrypted_bytes)
    return decrypted_bytes.decode("ascii")
