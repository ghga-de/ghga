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
from hvac.api.auth_methods import Kubernetes
from hvac.exceptions import InvalidPath
from testcontainers.core.generic import DockerContainer

from sms.core.secrets_handler import VaultConfig
from tests.fixtures.config import DEFAULT_TEST_CONFIG

DEFAULT_IMAGE = "hashicorp/vault:1.12"
VAULT_URL = DEFAULT_TEST_CONFIG.vault_url
DEFAULT_PORT = 8200
VAULT_PATH = DEFAULT_TEST_CONFIG.vault_path
VAULT_TOKEN = "dev-token"
VAULT_MOUNT_POINT = DEFAULT_TEST_CONFIG.vault_secrets_mount_point


class VaultFixture:
    """Contains initialized vault client.

    When a vault secret is stored, the vault path is stored in vaults_used.
    """

    def __init__(self, config: VaultConfig):
        self.config = config
        self.vaults_used: set[str] = set()
        self.client = hvac.Client(url=self.config.vault_url)
        self._auth_mount_point = config.vault_auth_mount_point
        self._secrets_mount_point = config.vault_secrets_mount_point
        self._kube_role = config.vault_kube_role

        if self._kube_role:
            # use kube role and service account token
            self._kube_adapter = Kubernetes(self.client.adapter)
            self._service_account_token_path = config.service_account_token_path
        elif config.vault_role_id and config.vault_secret_id:
            # use role and secret ID instead
            self._role_id = config.vault_role_id.get_secret_value()
            self._secret_id = config.vault_secret_id.get_secret_value()
        else:
            raise ValueError(
                "There is no way to log in to vault:\n"
                + "Neither kube role nor both role and secret ID were provided."
            )

    def _check_auth(self):
        """Check if authentication timed out and re-authenticate if needed"""
        if not self.client.is_authenticated():
            self._login()

    def _login(self):
        """Log in using Kubernetes Auth or AppRole"""
        if self._kube_role:
            with self._service_account_token_path.open() as token_file:
                jwt = token_file.read()
            if self._auth_mount_point:
                self._kube_adapter.login(
                    role=self._kube_role, jwt=jwt, mount_point=self._auth_mount_point
                )
            else:
                self._kube_adapter.login(role=self._kube_role, jwt=jwt)

        elif self._auth_mount_point:
            self.client.auth.approle.login(
                role_id=self._role_id,
                secret_id=self._secret_id,
                mount_point=self._auth_mount_point,
            )
        else:
            self.client.auth.approle.login(
                role_id=self._role_id, secret_id=self._secret_id
            )

    def store_secret(self, *, key: str, vault_path: str = VAULT_PATH):
        """Store a secret in vault"""
        self._check_auth()

        self.client.secrets.kv.v2.create_or_update_secret(
            path=f"{vault_path}/{key}",
            secret={key: f"secret_for_{key}"},
            mount_point=self.config.vault_secrets_mount_point,
        )
        self.vaults_used.add(vault_path)

    def delete_all_secrets(self, vault_path: str):
        """Remove all secrets from the vault to reset for next test"""
        self._check_auth()

        with suppress(InvalidPath):
            secrets = self.client.secrets.kv.v2.list_secrets(
                path=vault_path,
                mount_point=self.config.vault_secrets_mount_point,
            )
            for key in secrets["data"]["keys"]:
                self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                    path=f"{vault_path}/{key}",
                    mount_point=self.config.vault_secrets_mount_point,
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
        self.with_env("VAULT_ADDR", VAULT_URL)
        self.with_env("VAULT_DEV_ROOT_TOKEN_ID", VAULT_TOKEN)


class VaultContainerFixture(VaultContainer):
    """Fixture for VaultContainer"""

    config: VaultConfig


@pytest.fixture(scope="session", name="vault_container")
def vault_container_fixture() -> Generator[VaultContainerFixture, None, None]:
    """Generate preconfigured test container"""
    with VaultContainerFixture() as vault_container:
        host = vault_container.get_container_host_ip()
        port = vault_container.get_exposed_port(DEFAULT_PORT)
        role_id, secret_id = configure_vault(host=host, port=int(port))
        vault_container.config = VaultConfig(
            vault_url=f"http://{host}:{port}",
            vault_role_id=role_id,
            vault_secret_id=secret_id,
            vault_verify=DEFAULT_TEST_CONFIG.vault_verify,
            vault_path=VAULT_PATH,
            vault_secrets_mount_point=VAULT_MOUNT_POINT,
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


def configure_vault(*, host: str, port: int):
    """Configure vault using direct interaction with hvac.Client"""
    client = hvac.Client(url=f"http://{host}:{port}", token=VAULT_TOKEN)
    # client needs some time after creation
    time.sleep(2)

    # use a non-default secret engine to test configured secrets mount point
    client.sys.move_backend("secret", VAULT_MOUNT_POINT)

    # enable authentication with role_id/secret_id
    client.sys.enable_auth_method(
        method_type="approle",
    )

    # create access policy to bind to role
    policy = f"""
    path "{VAULT_MOUNT_POINT}/data/{VAULT_PATH}/*" {{
        capabilities = ["read", "list", "create", "update", "delete"]
    }}
    path "{VAULT_MOUNT_POINT}/metadata/{VAULT_PATH}/*" {{
        capabilities = ["read", "list", "create", "update", "delete"]
    }}
    """

    # inject policy
    client.sys.create_or_update_policy(name=VAULT_PATH, policy=policy)

    role_name = "test_role"
    # create role and bind policy
    response = client.auth.approle.create_or_update_approle(
        role_name=role_name,
        token_policies=[VAULT_PATH],
        token_type="service",
    )

    # retrieve role_id
    response = client.auth.approle.read_role_id(role_name=role_name)
    role_id = response["data"]["role_id"]

    # retrieve secret_id
    response = client.auth.approle.generate_secret_id(role_name=role_name)
    secret_id = response["data"]["secret_id"]

    # log out root token client
    client.logout()

    return role_id, secret_id
