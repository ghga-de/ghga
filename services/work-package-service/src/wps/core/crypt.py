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

"""Helper functions for encryption."""

import re

from ghga_service_commons.utils.crypt import decode_key

__all__ = ["validate_public_key"]


_re_pem_private = re.compile("-.*PRIVATE.*-")
_re_pem_public = re.compile("-----(BEGIN|END) CRYPT4GH PUBLIC KEY-----")


def validate_public_key(key: str) -> str:
    """Validate the given base64 encoded public key.

    Raises a ValueError if the given key is invalid as a public key.
    Also strips headers and footers from PEM format file.
    """
    if not key or not isinstance(key, str):
        raise ValueError("Key must be a non-empty string")
    if _re_pem_private.search(key):
        raise ValueError("Do not pass a private key")
    key = _re_pem_public.sub("", key).strip()
    decode_key(key)
    return key
