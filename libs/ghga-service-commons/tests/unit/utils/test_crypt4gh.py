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
"""Test Crypt4GH utility functions."""

import base64
import os
from pathlib import Path
from tempfile import mkstemp

from ghga_service_commons.utils.crypt4gh import (
    create_envelope,
    decrypt_file,
    extract_file_secret,
    generate_keypair,
    random_encrypted_content,
)

FILE_SIZE = 64 * 1024**2


def test_crypt4gh_utilities_bytes():
    """Test Crypt4GH functionality wrappers in sequence for bytes type arguments."""
    keypair = generate_keypair()

    file_secret = os.urandom(32)
    envelope = create_envelope(
        file_secret=file_secret,
        private_key=keypair.private,
        public_key=keypair.public,
    )
    extracted_secret = extract_file_secret(
        encrypted_header=envelope,
        private_key=keypair.private,
        public_key=keypair.public,
    )

    assert file_secret == extracted_secret

    test_data = random_encrypted_content(
        file_size=FILE_SIZE, private_key=keypair.private, public_key=keypair.public
    )

    file_secret = extract_file_secret(
        encrypted_header=test_data.content.read(1024**2),
        private_key=keypair.private,
        public_key=keypair.public,
    )
    assert len(file_secret) == 32

    _, inpath = mkstemp()
    _, outpath = mkstemp()

    test_data.content.seek(0)
    with open(inpath, "wb") as infile:
        infile.write(test_data.content.read())
        infile.seek(0)

    decrypt_file(input_path=inpath, output_path=outpath, private_key=keypair.private)
    with open(outpath, "rb") as out_file:
        assert len(out_file.read()) == test_data.decrypted_size

    decrypt_file(
        input_path=Path(inpath), output_path=Path(outpath), private_key=keypair.private
    )
    with open(outpath, "rb") as out_file:
        assert len(out_file.read()) == test_data.decrypted_size


def test_crypt4gh_utilities_str():
    """Test Crypt4GH functionality wrappers in sequence."""
    keypair = generate_keypair()

    private_key = base64.b64encode(keypair.private).decode()
    public_key = base64.b64encode(keypair.public).decode()
    file_secret = base64.b64encode(os.urandom(32)).decode()

    envelope = create_envelope(
        file_secret=file_secret,
        private_key=private_key,
        public_key=public_key,
    )

    envelope = base64.b64encode(envelope).decode()
    extracted_secret = extract_file_secret(
        encrypted_header=envelope,
        private_key=private_key,
        public_key=public_key,
    )

    assert base64.b64decode(file_secret) == extracted_secret

    test_data = random_encrypted_content(
        file_size=FILE_SIZE, private_key=keypair.private, public_key=keypair.public
    )

    test_data_envelope = base64.b64encode(test_data.content.read(1024**2)).decode()
    file_secret = extract_file_secret(
        encrypted_header=test_data_envelope,
        private_key=private_key,
        public_key=public_key,
    )
    assert len(file_secret) == 32

    _, inpath = mkstemp()
    _, outpath = mkstemp()

    test_data.content.seek(0)
    with open(inpath, "wb") as infile:
        infile.write(test_data.content.read())
        infile.seek(0)

    decrypt_file(input_path=inpath, output_path=outpath, private_key=private_key)
    with open(outpath, "rb") as out_file:
        assert len(out_file.read()) == test_data.decrypted_size

    decrypt_file(
        input_path=Path(inpath), output_path=Path(outpath), private_key=private_key
    )
    with open(outpath, "rb") as out_file:
        assert len(out_file.read()) == test_data.decrypted_size
