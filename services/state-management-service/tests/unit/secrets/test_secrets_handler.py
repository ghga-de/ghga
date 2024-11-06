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

"""Unit tests for the SecretsHandler class"""

from unittest.mock import Mock, call

import pytest
from hvac.exceptions import InvalidPath

from sms.core.secrets_handler import SecretsHandler
from tests.fixtures.config import DEFAULT_TEST_CONFIG
from tests.fixtures.vault import DEFAULT_VAULT_PATH


@pytest.mark.parametrize(
    "secrets",
    [[], ["key1"], ["key1", "key2"]],
    ids=["empty", "single", "multiple"],
)
def test_get_secrets(monkeypatch: pytest.MonkeyPatch, secrets: list[str]):
    """Test get_secrets method without errors"""
    # patch the hvac client with a mock
    mock_client = Mock()
    mock_client.secrets.kv.v2.list_secrets.return_value = {"data": {"keys": secrets}}
    monkeypatch.setattr(SecretsHandler, "client", mock_client)
    secrets_handler = SecretsHandler(config=DEFAULT_TEST_CONFIG)

    assert secrets_handler.get_secrets(DEFAULT_VAULT_PATH) == secrets
    mock_client.secrets.kv.v2.list_secrets.assert_called_once()


def test_get_secrets_error(monkeypatch: pytest.MonkeyPatch, caplog):
    """Test get_secrets method with an error"""
    # patch the hvac client with a mock
    mock_client = Mock()
    mock_client.secrets.kv.v2.list_secrets.side_effect = InvalidPath("Invalid path")
    monkeypatch.setattr(SecretsHandler, "client", mock_client)
    secrets_handler = SecretsHandler(config=DEFAULT_TEST_CONFIG)

    # Make sure the error is logged as a warning but an empty list is still returned
    caplog.clear()
    secrets = secrets_handler.get_secrets(DEFAULT_VAULT_PATH)
    assert len(caplog.messages) == 1
    assert caplog.messages[0] == (
        f"Invalid path error when fetching secrets. The path, '{DEFAULT_VAULT_PATH}',"
        + " might be invalid, or no secrets may exist."
    )
    assert caplog.records[0].levelname == "WARNING"
    assert secrets == []
    mock_client.secrets.kv.v2.list_secrets.assert_called_once()


def test_delete_secrets_error(monkeypatch: pytest.MonkeyPatch):
    """Test delete_secrets method on empty vault."""
    # patch the hvac client with a mock
    mock_client = Mock()
    mock_client.secrets.kv.v2.list_secrets.side_effect = InvalidPath("Invalid path")
    monkeypatch.setattr(SecretsHandler, "client", mock_client)
    secrets_handler = SecretsHandler(config=DEFAULT_TEST_CONFIG)

    # Call delete_secrets() in order to trigger get_secrets
    secrets_handler.delete_secrets(DEFAULT_VAULT_PATH)
    mock_client.secrets.kv.v2.list_secrets.assert_called_once()
    mock_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_not_called()


@pytest.mark.parametrize(
    "stored_secrets",
    [[], ["key1"], ["key1", "key2"]],
    ids=["Empty", "OneSecret", "TwoSecrets"],
)
def test_delete_successful(
    monkeypatch: pytest.MonkeyPatch,
    stored_secrets: list[str],
):
    """Test delete_secrets method."""
    # create a mock for the hvac client
    list_stored_secrets = {"data": {"keys": stored_secrets}}
    mock_client = Mock()

    # list_secrets either returns all keys or raises an InvalidPath error
    if stored_secrets:
        mock_client.secrets.kv.v2.list_secrets.return_value = list_stored_secrets
    else:
        mock_client.secrets.kv.v2.list_secrets.side_effect = InvalidPath("Invalid path")

    # apply the mock to the SecretsHandler
    monkeypatch.setattr(SecretsHandler, "client", mock_client)
    secrets_handler = SecretsHandler(config=DEFAULT_TEST_CONFIG)

    # call delete_secrets()
    secrets_handler.delete_secrets(DEFAULT_VAULT_PATH)
    mock_client.secrets.kv.v2.list_secrets.assert_called_once()

    # delete_metadata_and_all_versions is called for each secret
    internal_deletion_calls = [
        call(
            path=f"{DEFAULT_VAULT_PATH}/{secret}",
            mount_point=DEFAULT_TEST_CONFIG.vault_secrets_mount_point,
        )
        for secret in stored_secrets
    ]
    mock_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_has_calls(
        internal_deletion_calls,
        any_order=True,
    )


def test_non_default_mount_point(monkeypatch: pytest.MonkeyPatch):
    """Test get_secrets and delete_secrets method with non-default mount point.

    Makes sure that the actual config value is passed to the hvac Client.
    """
    mock_client = Mock()
    list_stored_secrets = {"data": {"keys": ["key1"]}}
    mock_client.secrets.kv.v2.list_secrets.return_value = list_stored_secrets

    # apply the mock to the SecretsHandler
    monkeypatch.setattr(SecretsHandler, "client", mock_client)

    # use alternative mount point
    mount_point = "test"
    config = DEFAULT_TEST_CONFIG.model_copy(
        update={"vault_secrets_mount_point": mount_point}
    )
    secrets_handler = SecretsHandler(config=config)

    # call delete_secrets()
    secrets_handler.delete_secrets(f"{DEFAULT_VAULT_PATH}")
    mock_client.secrets.kv.v2.list_secrets.assert_called_once_with(
        path=f"{DEFAULT_VAULT_PATH}",
        mount_point=mount_point,
    )

    mock_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once_with(
        path=f"{DEFAULT_VAULT_PATH}/key1",
        mount_point=mount_point,
    )
