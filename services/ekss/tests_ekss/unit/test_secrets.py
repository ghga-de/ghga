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

"""Unit tests for the SecretsHandler"""

import io
import os
from unittest.mock import AsyncMock

import crypt4gh.header
import pytest

from ekss.core.secrets import SecretsHandler
from ekss.ports.inbound.secrets import SecretsHandlerPort
from ekss.ports.outbound.vault import VaultClientPort
from tests_ekss.fixtures.config import get_config
from tests_ekss.fixtures.keypair import KeypairFixture
from tests_ekss.fixtures.utils import make_secret_payload


def test_get_envelope(keypair: KeypairFixture):
    """Test the .get_envelope() method for both error handling and success case"""
    config = get_config([keypair.config])
    vault_client = AsyncMock(spec=VaultClientPort)
    secrets_handler = SecretsHandler(config=config, vault_client=vault_client)

    # Mock the vault client to raise VaultClientPort.SecretRetrievalError
    vault_client.get_secret.side_effect = VaultClientPort.SecretRetrievalError
    with pytest.raises(SecretsHandlerPort.SecretRetrievalError):
        _ = secrets_handler.get_envelope(
            secret_id="some-secret-id", client_pubkey=keypair.user_pk
        )

    # Call without mocking the secret - this will cause envelope creation to fail
    vault_client.get_secret.side_effect = None
    with pytest.raises(SecretsHandlerPort.EnvelopeCreationError):
        _ = secrets_handler.get_envelope(
            secret_id="some-secret-id", client_pubkey=keypair.user_pk
        )

    # Mock the secret
    secret = os.urandom(32)
    vault_client.get_secret.return_value = secret
    envelope = secrets_handler.get_envelope(
        secret_id="some-secret-id", client_pubkey=keypair.user_pk
    )

    # Inspect the envelope like in the integration test
    keys = [(0, keypair.user_sk, None)]
    session_keys, _ = crypt4gh.header.deconstruct(
        infile=io.BytesIO(envelope), keys=keys
    )
    assert session_keys[0] == secret


def test_deposit_secret(keypair: KeypairFixture):
    """Test the .deposit_secret() method for both error handling and success case"""
    config = get_config([keypair.config])
    vault_client = AsyncMock(spec=VaultClientPort)
    secrets_handler = SecretsHandler(config=config, vault_client=vault_client)

    # Test SecretDecryptionError - pass garbage that can't be decrypted
    with pytest.raises(SecretsHandlerPort.SecretDecryptionError):
        _ = secrets_handler.deposit_secret(encrypted_secret="not-valid-crypt4gh")

    # Prepare a valid encrypted payload for the remaining cases
    file_secret, encrypted = make_secret_payload(keypair.ekss_pk)
    # Test SecretInsertionError - vault raises on store
    vault_client.store_secret.side_effect = VaultClientPort.SecretInsertionError
    with pytest.raises(SecretsHandlerPort.SecretInsertionError):
        _ = secrets_handler.deposit_secret(encrypted_secret=encrypted)

    # Test success - vault returns a secret_id
    vault_client.store_secret.reset_mock()
    vault_client.store_secret.side_effect = None
    vault_client.store_secret.return_value = "test-secret-id"
    secret_id = secrets_handler.deposit_secret(encrypted_secret=encrypted)
    assert secret_id == "test-secret-id"
    vault_client.store_secret.assert_called_once_with(secret=file_secret)


def test_delete_secret(keypair: KeypairFixture):
    """Test the .delete_secret() method for both error handling and success case"""
    config = get_config([keypair.config])
    vault_client = AsyncMock(spec=VaultClientPort)
    secrets_handler = SecretsHandler(config=config, vault_client=vault_client)

    # Test SecretRetrievalError - secret not found in vault
    vault_client.delete_secret.side_effect = VaultClientPort.SecretRetrievalError
    with pytest.raises(SecretsHandlerPort.SecretRetrievalError):
        secrets_handler.delete_secret(secret_id="test-secret-id")

    # Test SecretDeletionError - secret found but deletion failed
    vault_client.delete_secret.side_effect = VaultClientPort.SecretDeletionError
    with pytest.raises(SecretsHandlerPort.SecretDeletionError):
        secrets_handler.delete_secret(secret_id="test-secret-id")

    # Test success - vault deletes without error and raises no error either
    vault_client.delete_secret.side_effect = None
    secrets_handler.delete_secret(secret_id="test-secret-id")
    vault_client.delete_secret.assert_called_with(key="test-secret-id")
