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

"""Test file operations"""

import base64
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import crypt4gh.keys
import pytest
from ghga_service_commons.utils.temp_files import big_temp_file

from ghga_connector.core import is_file_encrypted, read_file_parts
from ghga_connector.core.crypt import Crypt4GHDecryptor, Crypt4GHEncryptor
from ghga_connector.core.utils import get_private_key


@pytest.mark.parametrize("from_part", (None, 3))
def test_read_file_parts(from_part: int | None):
    """Test reading a full file with the `read_file_parts` function."""
    file_size = 20 * 1024 * 1024
    part_size = 5 * 1024 * 1024

    with big_temp_file(file_size) as file:
        # Get the expected content:
        initial_offset = 0 if from_part is None else part_size * (from_part - 1)
        file.seek(initial_offset)
        expected_content = file.read()
        file.seek(0)

        # read the file in parts:
        obtained_content = b""
        file_parts = (
            read_file_parts(file, part_size=part_size)  # type: ignore
            if from_part is None
            else read_file_parts(file, part_size=part_size, from_part=from_part)  # type: ignore
        )

        for part in file_parts:
            obtained_content += part

        assert expected_content == obtained_content


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

    passphrase = "test" if sk_name.startswith("encrypted") else None
    private_key = get_private_key(private_key_path, passphrase=passphrase)

    pubkey = base64.b64encode(crypt4gh.keys.get_public_key(pubkey_path)).decode("utf-8")
    monkeypatch.setattr(
        "ghga_connector.core.crypt.encryption.get_ghga_pubkey", lambda: pubkey
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
        )
        for chunk in encryptor.process_file(file=in_file):  # type: ignore
            encrypted_file.write(chunk[1])

        # rewind file and check if file is recognized as encrypted
        in_file.seek(0)
        encrypted_file_loc = Path(encrypted_file.name)
        assert is_file_encrypted(encrypted_file_loc)

        # decrypt file and verifies it matches initial input
        decryptor = Crypt4GHDecryptor(
            decryption_key_path=private_key_path, passphrase=passphrase
        )
        decryptor.decrypt_file(
            input_path=encrypted_file_loc,
            output_path=Path(out_file.name),
        )

        assert in_file.read() == out_file.read()
