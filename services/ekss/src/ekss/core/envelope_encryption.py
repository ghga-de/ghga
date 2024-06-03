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

"""Implements functionality for envelope encrytion"""

import base64

import crypt4gh.header

from ekss.adapters.outbound.vault import VaultAdapter
from ekss.config import CONFIG


async def get_envelope(
    *, secret_id: str, client_pubkey: bytes, vault: VaultAdapter
) -> bytes:
    """Calls the database and then calls a function to assemble an envelope"""
    file_secret = vault.get_secret(key=secret_id)
    header_envelope = await create_envelope(
        file_secret=file_secret, client_pubkey=client_pubkey
    )

    return header_envelope


async def create_envelope(*, file_secret: bytes, client_pubkey: bytes) -> bytes:
    """
    Gather file encryption/decryption secret and assemble a crypt4gh envelope using the
    servers private and the clients public key
    """
    server_private_key = base64.b64decode(CONFIG.server_private_key.get_secret_value())
    keys = [(0, server_private_key, client_pubkey)]
    header_content = crypt4gh.header.make_packet_data_enc(0, file_secret)
    header_packets = crypt4gh.header.encrypt(header_content, keys)
    header_bytes = crypt4gh.header.serialize(header_packets)

    return header_bytes
