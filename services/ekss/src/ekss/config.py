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

"""Config Parameter Modeling and Parsing"""

import base64
from pathlib import Path

from ghga_service_commons.api import ApiConfigBase
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


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


@config_from_yaml(prefix="ekss")
class Config(ApiConfigBase, VaultConfig, LoggingConfig):
    """Config parameters and their defaults."""

    service_name: str = "encryption_key_store"
    server_private_key: SecretStr = Field(
        default=...,
        examples=["server_private_key"],
        description="Base64 encoded server Crypt4GH private key",
    )
    server_public_key: str = Field(
        default=...,
        examples=["server_public_key"],
        description="Base64 encoded server Crypt4GH public key",
    )

    @field_validator("server_private_key")
    @classmethod
    def validate_private_key_parsable(cls, value: SecretStr):
        """Try do decode public key using base64 and check if length matches expectations."""
        secret_value = value.get_secret_value()
        decoded = base64.b64decode(secret_value)
        key_length = len(decoded)
        if key_length != 32:
            raise ValueError(
                f"Length of decoded private key did not match expectation:\nIs:{key_length}\nShould be: 32"
            )
        return value

    @field_validator("server_public_key")
    @classmethod
    def validate_public_key_parsable(cls, value: str):
        """Try do decode public key using base64 and check if length matches expectations."""
        decoded = base64.b64decode(value)
        key_length = len(decoded)
        if key_length != 32:
            raise ValueError(
                f"Length of decoded public key did not match expectation:\nIs:{key_length}\nShould be: 32"
            )
        return value


CONFIG = Config()  # type: ignore [call-arg]
