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
"""Implements functionality for envelope decryption and secret storage"""

import base64
import io

import crypt4gh.header

from ekss.config import CONFIG


async def extract_envelope_content(
    *, file_part: bytes, client_pubkey: bytes
) -> tuple[bytes, int]:
    """Extract file encryption/decryption secret and file content offset from envelope"""
    envelope_stream = io.BytesIO(file_part)

    server_private_key = base64.b64decode(CONFIG.server_private_key.get_secret_value())
    # (method - only 0 supported for now, private_key, public_key)
    keys = [(0, server_private_key, None)]
    session_keys, _ = crypt4gh.header.deconstruct(
        infile=envelope_stream, keys=keys, sender_pubkey=client_pubkey
    )

    submitter_secret = session_keys[0]
    offset = envelope_stream.tell()

    return submitter_secret, offset
