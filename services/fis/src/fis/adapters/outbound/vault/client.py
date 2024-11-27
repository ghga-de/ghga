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
"""Provides client side functionality for interaction with HashiCorp Vault"""

from pathlib import Path
from uuid import uuid4

import hvac
import hvac.exceptions
from hvac.api.auth_methods import Kubernetes
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

from fis.ports.outbound.vault.client import VaultAdapterPort


class VaultConfig(BaseSettings):
    """Configuration for HashiCorp Vault connection"""

    vault_url: str = Field(
        default=...,
        examples=["http://127.0.0.1.8200"],
        description="URL of the vault instance to connect to",
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
    vault_secrets_mount_point: str = Field(
        default="secret",
        examples=["secret"],
        description="Name used to address the secret engine under a custom mount path.",
    )
    vault_kube_role: str | None = Field(
        default=None,
        examples=["file-ingest-role"],
        description="Vault role name used for Kubernetes authentication",
    )
    vault_auth_mount_point: str | None = Field(
        default=None,
        examples=[None, "approle", "kubernetes"],
        description="Adapter specific mount path for the corresponding auth backend."
        " If none is provided, the default is used.",
    )
    service_account_token_path: Path = Field(
        default=Path("/var/run/secrets/kubernetes.io/serviceaccount/token"),
        description="Path to service account token used by kube auth adapter.",
    )


class VaultAdapter(VaultAdapterPort):
    """Adapter wrapping hvac.Client"""

    def __init__(self, config: VaultConfig):
        """Initialized approle based client and login"""
        self._client = hvac.Client(url=config.vault_url, verify=config.vault_verify)
        self._path = config.vault_path
        self._auth_mount_point = config.vault_auth_mount_point
        self._secrets_mount_point = config.vault_secrets_mount_point

        self._kube_role = config.vault_kube_role
        if self._kube_role:
            # use kube role and service account token
            self._kube_adapter = Kubernetes(self._client.adapter)
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
        if not self._client.is_authenticated():
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
            self._client.auth.approle.login(
                role_id=self._role_id,
                secret_id=self._secret_id,
                mount_point=self._auth_mount_point,
            )
        else:
            self._client.auth.approle.login(
                role_id=self._role_id, secret_id=self._secret_id
            )

    def store_secret(self, *, secret: SecretStr) -> str:
        """
        Store a secret under a subpath of the given prefix.
        Generates a UUID4 as key, uses it for the subpath and returns it.
        """
        key = str(uuid4())

        self._check_auth()

        try:
            # set cas to 0 as we only want a static secret
            self._client.secrets.kv.v2.create_or_update_secret(
                path=f"{self._path}/{key}",
                secret={key: secret.get_secret_value()},
                cas=0,
                mount_point=self._secrets_mount_point,
            )
        except hvac.exceptions.InvalidRequest as exc:
            raise self.SecretInsertionError() from exc
        return key

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
