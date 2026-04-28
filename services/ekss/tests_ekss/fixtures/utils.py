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

"""General testing utilities"""

import base64
import os
from pathlib import Path

from ghga_service_commons.utils.crypt import encrypt

BASE_DIR = Path(__file__).parent.resolve()


def make_secret_payload(ekss_pk: bytes) -> tuple[bytes, str]:
    """Returns a tuple containing a raw 32-byte file secret and the base64-encoded
    crypt4gh-encrypted version of the same secret.
    """
    file_secret = os.urandom(32)
    encoded_secret = base64.urlsafe_b64encode(file_secret).decode("utf-8")
    encrypted_secret = encrypt(encoded_secret, key=ekss_pk, encoding="utf-8")
    return (file_secret, encrypted_secret)
