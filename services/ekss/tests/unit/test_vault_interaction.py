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
"""Test HashiCorp Vault interaction"""

import os

import pytest

from ekss.adapters.outbound.vault.exceptions import SecretRetrievalError
from tests.fixtures.vault import (
    VaultFixture,
    vault_fixture,  # noqa: F401
)


def test_connection(vault_fixture: VaultFixture):  # noqa: F811
    """Test if container is up and reachable and commands are working"""
    # populate
    secret = os.urandom(32)
    secret2 = os.urandom(32)
    secret_id = vault_fixture.adapter.store_secret(secret=secret)
    secret2_id = vault_fixture.adapter.store_secret(secret=secret2)

    # test retrieval
    stored_secret = vault_fixture.adapter.get_secret(key=secret_id)
    assert secret == stored_secret

    # test deletion
    vault_fixture.adapter.delete_secret(key=secret_id)
    with pytest.raises(SecretRetrievalError):
        vault_fixture.adapter.get_secret(key=secret_id)

    # test deletion only affected correct path
    stored_secret2 = vault_fixture.adapter.get_secret(key=secret2_id)
    assert secret2 == stored_secret2
