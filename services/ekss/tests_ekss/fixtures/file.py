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
"""First-file-part fixture"""

import io
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import crypt4gh.lib
import pytest_asyncio
from crypt4gh.keys import get_private_key, get_public_key
from ghga_service_commons.utils import temp_files

from ekss.config import Config
from tests_ekss.fixtures.config import DEFAULT_CONFIG, get_config
from tests_ekss.fixtures.keypair import tmp_keypair
from tests_ekss.fixtures.vault import (
    VaultFixture,
    vault_fixture,  # noqa: F401
)


@dataclass
class FirstPartFixture:
    """Fixture for envelope extraction"""

    config: Config
    client_pubkey: bytes
    content: bytes
    vault: VaultFixture


@pytest_asyncio.fixture
async def first_part_fixture(
    *,
    vault_fixture: VaultFixture,  # noqa: F811
) -> AsyncGenerator[FirstPartFixture, None]:
    """Create random File, encrypt with Crypt4GH, return DAOs, secrets and first file part"""
    file_size = 20 * 1024**2
    part_size = 16 * 1024**2

    with (
        temp_files.big_temp_file(file_size) as raw_file,
        io.BytesIO() as encrypted_file,
        tmp_keypair(DEFAULT_CONFIG.private_key_passphrase) as crypt4gh_config,
    ):
        config = get_config([vault_fixture.config, crypt4gh_config])
        server_pubkey = get_public_key(config.server_public_key_path)
        private_key = get_private_key(
            config.server_private_key_path,
            callback=lambda: config.private_key_passphrase,
        )
        keys = [(0, private_key, server_pubkey)]
        # rewind input file for reading
        raw_file.seek(0)
        crypt4gh.lib.encrypt(keys=keys, infile=raw_file, outfile=encrypted_file)
        # rewind output file for reading
        encrypted_file.seek(0)
        part = encrypted_file.read(part_size)
        public_key = get_public_key(config.server_public_key_path)
        yield FirstPartFixture(
            config=config,
            client_pubkey=public_key,
            content=part,
            vault=vault_fixture,
        )
