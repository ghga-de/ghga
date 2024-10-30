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
"""HashiCorp vault fixture for testing"""

import time
from collections.abc import Generator
from contextlib import suppress

import hvac
import pytest
from hvac.exceptions import InvalidPath
from testcontainers.core.generic import DockerContainer

from sms.core.secrets_handler import VaultConfig

DEFAULT_IMAGE = "hashicorp/vault:1.12"
DEFAULT_URL = "http://0.0.0.0:8200"
DEFAULT_PORT = 8200
DEFAULT_TOKEN = "dev-token"
DEFAULT_VAULT_PATH = "sms"


class VaultFixture:
    """Contains initialized vault client.

    When a vault secret is stored, the vault path is stored in vaults_used.
    """

    def __init__(self, config: VaultConfig):
        self.config = config
        self.vaults_used: set[str] = set()

    def store_secret(self, *, key: str, vault_path: str = DEFAULT_VAULT_PATH):
        """Store a secret in vault"""
        client = hvac.Client(url=self.config.vault_url, token=DEFAULT_TOKEN)

        client.secrets.kv.v2.create_or_update_secret(
            path=f"{vault_path}/{key}",
            secret={key: f"secret_for_{key}"},
        )
        self.vaults_used.add(vault_path)

    def delete_all_secrets(self, vault_path: str):
        """Remove all secrets from the vault to reset for next test"""
        client = hvac.Client(url=self.config.vault_url, token=DEFAULT_TOKEN)

        with suppress(InvalidPath):
            secrets = client.secrets.kv.v2.list_secrets(path=vault_path)
            for key in secrets["data"]["keys"]:
                client.secrets.kv.v2.delete_metadata_and_all_versions(
                    path=f"{vault_path}/{key}"
                )

    def reset(self):
        """Reset the vault for next test"""
        for vault_path in self.vaults_used:
            self.delete_all_secrets(vault_path)
        self.vaults_used.clear()


class VaultContainer(DockerContainer):
    """A hashi corp vault container for testing."""

    def __init__(self, image: str = DEFAULT_IMAGE, port: int = DEFAULT_PORT, **kwargs):
        """Initialize a vault container with default settings."""
        super().__init__(image, **kwargs)

        self.with_exposed_ports(port)
        self.with_env("VAULT_ADDR", DEFAULT_URL)
        self.with_env("VAULT_DEV_ROOT_TOKEN_ID", DEFAULT_TOKEN)


class VaultContainerFixture(VaultContainer):
    """Fixture for VaultContainer"""

    config: VaultConfig


@pytest.fixture(scope="session", name="vault_container")
def vault_container_fixture() -> Generator[VaultContainerFixture, None, None]:
    """Generate preconfigured test container"""
    with VaultContainerFixture() as vault_container:
        host = vault_container.get_container_host_ip()
        port = vault_container.get_exposed_port(DEFAULT_PORT)
        vault_container.config = VaultConfig(
            vault_url=f"http://{host}:{port}",
            vault_token=DEFAULT_TOKEN,
        )

        # client needs some time after creation
        time.sleep(2)
        yield vault_container


@pytest.fixture(scope="function", name="vault")
def vault_fixture(
    vault_container: VaultContainerFixture,
) -> Generator[VaultFixture, None, None]:
    """Fixture function to produce a VaultFixture"""
    vault = VaultFixture(config=vault_container.config)
    vault.reset()
    yield vault
