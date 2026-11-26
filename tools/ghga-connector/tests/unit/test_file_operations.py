# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test file operations"""

import base64
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import crypt4gh.keys
import pytest
from pydantic import SecretStr

from ghga_connector.core import is_file_encrypted
from ghga_connector.core.crypt import Crypt4GHEncryptor
from ghga_connector.core.main import decrypt_file
from ghga_connector.core.utils import get_private_key
from tests.fixtures.utils import TEST_STORAGE_ALIAS1


@pytest.mark.parametrize(
    "pk_name,sk_name",
    [("key.pub", "key.sec"), ("encrypted_key.pub", "encrypted_key.sec")],
)
@pytest.mark.asyncio
async def test_encryption_decryption(
    pk_name: str,
    sk_name: str,
    monkeypatch,
):
    """Encrypt and decrypt a file to check if it is actually encrypted"""
    file_size = 20 * 1024 * 1024
    key_dir = Path(__file__).parent.parent / "fixtures" / "keypair"
    pubkey_path = key_dir / pk_name
    private_key_path = key_dir / sk_name

    passphrase = SecretStr("test") if sk_name.startswith("encrypted") else None
    if passphrase:
        monkeypatch.setattr(
            "ghga_connector.core.utils.make_passphrase_callback",
            lambda tries_left: lambda: passphrase.get_secret_value(),
        )
    private_key = get_private_key(private_key_path)

    pubkey = base64.b64encode(crypt4gh.keys.get_public_key(pubkey_path)).decode("utf-8")
    monkeypatch.setattr(
        "ghga_connector.core.crypt.encryption.get_crypt4gh_public_key",
        lambda storage_alias: pubkey,
    )

    with (
        NamedTemporaryFile() as in_file,
        NamedTemporaryFile() as encrypted_file,
        NamedTemporaryFile() as out_file,
    ):
        # fill source file with random data
        in_file.write(os.urandom(file_size))
        in_file.seek(0)

        # produce encrypted file
        encryptor = Crypt4GHEncryptor(
            part_size=8 * 1024**3,
            my_private_key=private_key,
            file_size=file_size,
            storage_alias=TEST_STORAGE_ALIAS1,
        )
        for chunk in encryptor.process_file(file=in_file):  # type: ignore
            encrypted_file.write(chunk[1])

        # rewind file and check if file is recognized as encrypted
        in_file.seek(0)
        encrypted_file_loc = Path(encrypted_file.name)
        assert is_file_encrypted(encrypted_file_loc)

        # we already have the pk loaded, so mock patch get_private_key to return it directly
        monkeypatch.setattr(
            "ghga_connector.core.utils.get_private_key",
            lambda x: private_key,
        )

        # decrypt file and verifies it matches initial input
        decrypt_file(
            input_file=encrypted_file_loc,
            output_file=Path(out_file.name),
            decryption_private_key_path=private_key_path,
        )

        assert in_file.read() == out_file.read()
