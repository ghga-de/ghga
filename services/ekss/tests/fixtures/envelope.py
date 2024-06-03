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
"""Envelope test fixture for public keys/secrets"""

import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio

from tests.fixtures.keypair import (
    KeypairFixture,
    generate_keypair_fixture,  # noqa: F401
)
from tests.fixtures.vault import (
    VaultFixture,
    vault_fixture,  # noqa: F401
)


@dataclass
class EnvelopeFixture:
    """Fixture for GET call to create an envelope"""

    client_pk: bytes
    client_sk: bytes
    secret_id: str
    secret: bytes
    vault: VaultFixture


@pytest_asyncio.fixture
async def envelope_fixture(
    *,
    vault_fixture: VaultFixture,  # noqa: F811
    generate_keypair_fixture: KeypairFixture,  # noqa: F811
) -> AsyncGenerator[EnvelopeFixture, None]:
    """
    Generates an EnvelopeFixture, containing a client public key as well as a secret id
    That secret id corresponds to a random secret created and put into the database
    """
    secret = os.urandom(32)

    # put secret in database
    secret_id = vault_fixture.adapter.store_secret(secret=secret)

    yield EnvelopeFixture(
        client_pk=generate_keypair_fixture.public_key,
        client_sk=generate_keypair_fixture.private_key,
        secret_id=secret_id,
        secret=secret,
        vault=vault_fixture,
    )
