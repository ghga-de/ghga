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
"""Provides a fixture around MongoDB, prefilling the DB with test data"""

import os
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from crypt4gh.keys import get_private_key, get_public_key
from crypt4gh.keys.c4gh import generate as generate_keypair

from ekss.config import Crypt4GHConfig
from tests_ekss.fixtures.config import DEFAULT_CONFIG


@dataclass
class KeypairFixture:
    """A fixture that contains a temporary Crypt4GH keypair and the key file paths"""

    ekss_pk_path: Path
    ekss_sk_path: Path
    ekss_pk: bytes
    ekss_sk: bytes
    user_pk: bytes
    user_sk: bytes
    config: Crypt4GHConfig


@pytest.fixture(name="keypair")
def keypair_fixture() -> Generator[KeypairFixture]:
    """Creates a keypair in tmp using crypt4gh and yields a KeypairFixture with the file
    paths and the values
    """
    # Crypt4GH always writes to file and umask inside of its code causes permission issues
    with TemporaryDirectory() as tempdir:
        pk_path = Path(tempdir) / "pub.key"
        sk_path = Path(tempdir) / "sec.key"

        user_pk_path = Path(tempdir) / "user_pub.key"
        user_sk_path = Path(tempdir) / "user_sec.key"

        # Crypt4GH does not reset the umask it sets, so we need to deal with it
        # umask returns the current value before setting the specified mask
        original_umask = os.umask(0o022)
        passphrase = DEFAULT_CONFIG.private_key_passphrase
        if passphrase:
            generate_keypair(
                seckey=sk_path,
                pubkey=pk_path,
                passphrase=passphrase.encode(),
                comment=None,
            )
            generate_keypair(
                seckey=user_sk_path,
                pubkey=user_pk_path,
                passphrase=passphrase.encode(),
                comment=None,
            )
        else:
            generate_keypair(
                seckey=sk_path, pubkey=pk_path, passphrase=None, comment=None
            )
            generate_keypair(
                seckey=user_sk_path, pubkey=user_pk_path, passphrase=None, comment=None
            )
        os.umask(original_umask)

        ekss_sk = get_private_key(sk_path, callback=lambda: passphrase)
        ekss_pk = get_public_key(pk_path)
        user_sk = get_private_key(user_sk_path, callback=lambda: passphrase)
        user_pk = get_public_key(user_pk_path)

        yield KeypairFixture(
            ekss_pk_path=pk_path,
            ekss_sk_path=sk_path,
            ekss_pk=ekss_pk,
            ekss_sk=ekss_sk,
            user_pk=user_pk,
            user_sk=user_sk,
            config=Crypt4GHConfig(
                server_private_key_path=sk_path, private_key_passphrase=passphrase
            ),
        )
