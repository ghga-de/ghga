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
"""Implementation of the SecretsHandlerPort"""

import logging
from pathlib import Path

from hvac import Client as HvacClient
from hvac.api.auth_methods import Kubernetes
from hvac.exceptions import InvalidPath
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

from sms.ports.inbound.secrets_handler import SecretsHandlerPort

log = logging.getLogger(__name__)


class VaultConfig(BaseSettings):
    """Configuration for the vault client"""

    vault_url: str = Field(
        default=..., description="URL for the Vault", examples=["http://vault:8200"]
    )
    vault_token: str = Field(
        default=..., description="Token for the Vault", examples=["dev-token"]
    )
    vault_secrets_mount_point: str = Field(
        default="secret",
        examples=["secret"],
        description="Name used to address the secret engine under a custom mount path.",
    )
    vault_role_id: SecretStr | None = Field(
        default=None,
        examples=["example_role"],
        description="Vault role ID to access a specific prefix",
    )
    vault_secret_id: SecretStr | None = Field(
        default=None,
        examples=["example_secret"],
        description="Vault secret ID to access a specific prefix",
    )
    vault_verify: bool | str = Field(
        default=True,
        examples=["/etc/ssl/certs/my_bundle.pem"],
        description="SSL certificates (CA bundle) used to"
        " verify the identity of the vault, or True to"
        " use the default CAs, or False for no verification.",
    )
    vault_path: str = Field(
        default=...,
        description="Path without leading or trailing slashes where secrets should"
        + " be stored in the vault.",
    )
    vault_kube_role: str | None = Field(
        default=None,
        examples=["file-ingest-role"],
        description="Vault role name used for Kubernetes authentication",
    )
    vault_auth_mount_point: str | None = Field(
        default=None,
        examples=[None, "approle", "kubernetes"],
        description=(
            "Adapter specific mount path for the corresponding auth backend."
            + " If none is provided, the default is used."
        ),
    )
    service_account_token_path: Path = Field(
        default="/var/run/secrets/kubernetes.io/serviceaccount/token",
        description="Path to service account token used by kube auth adapter.",
    )


class SecretsHandler(SecretsHandlerPort):
    """Adapter wrapping hvac.Client"""

    def __init__(self, config: VaultConfig):
        """Initialized approle-based client and log in"""
        self._config = config
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

    @field_validator("vault_verify")
    @classmethod
    def validate_vault_ca(cls, value: bool | str) -> bool | str:
        """Check that the CA bundle can be read if it is specified."""
        if isinstance(value, str):
            path = Path(value)
            if not path.exists():
                raise ValueError(f"Vault CA bundle not found at: {path}")
            try:
                bundle = path.open().read()
            except OSError as error:
                raise ValueError("Vault CA bundle cannot be read") from error
            if "-----BEGIN CERTIFICATE-----" not in bundle:
                raise ValueError("Vault CA bundle does not contain a certificate")
        return value

    @property
    def client(self) -> HvacClient:
        """Return an instance of a vault client"""
        return HvacClient(
            url=self._config.vault_url,
            token=self._config.vault_token,
            verify=self._config.vault_verify,
        )

    def get_secrets(self, vault_path: str) -> list[str]:
        """Return the IDs of all secrets in the specified vault."""
        self._check_auth()

        try:
            secrets = self.client.secrets.kv.v2.list_secrets(
                path=vault_path,
                mount_point=self._config.vault_secrets_mount_point,
            )
            secret_ids = secrets["data"]["keys"]
            return secret_ids
        except InvalidPath:
            msg = (
                "Invalid path error when fetching secrets. The path, '%s', might"
                + " be invalid, or no secrets may exist."
            )
            log.warning(msg, vault_path)
            return []

    def delete_secrets(self, vault_path: str):
        """Delete all secrets from the specified vault."""
        secrets = self.get_secrets(vault_path)

        if not secrets:
            log.info("No secrets to delete from vault path '%s'", vault_path)
            return

        for secret in secrets:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=f"{vault_path}/{secret}",
                mount_point=self._config.vault_secrets_mount_point,
            )
