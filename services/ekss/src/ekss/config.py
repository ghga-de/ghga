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

"""Config Parameter Modeling and Parsing"""

from pathlib import Path
from typing import Optional, Union

from ghga_service_commons.api import ApiConfigBase
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class VaultConfig(BaseSettings):
    """Configuration for HashiCorp Vault connection"""

    vault_url: str = Field(
        ...,
        examples=["http://127.0.0.1.8200"],
        description="URL of the vault instance to connect to",
    )
    vault_role_id: Optional[SecretStr] = Field(
        default=None,
        examples=["example_role"],
        description="Vault role ID to access a specific prefix",
    )
    vault_secret_id: Optional[SecretStr] = Field(
        default=None,
        examples=["example_secret"],
        description="Vault secret ID to access a specific prefix",
    )
    vault_verify: Union[bool, str] = Field(
        True,
        examples=["/etc/ssl/certs/my_bundle.pem"],
        description="SSL certificates (CA bundle) used to"
        " verify the identity of the vault, or True to"
        " use the default CAs, or False for no verification.",
    )
    vault_path: str = Field(
        ...,
        description="Path without leading or trailing slashes where secrets should"
        + " be stored in the vault.",
    )
    vault_secrets_mount_point: str = Field(
        default="secret",
        examples=["secret"],
        description="Name used to address the secret engine under a custom mount path.",
    )
    vault_kube_role: Optional[str] = Field(
        default=None,
        examples=["file-ingest-role"],
        description="Vault role name used for Kubernetes authentication",
    )
    service_account_token_path: Path = Field(
        default="/var/run/secrets/kubernetes.io/serviceaccount/token",
        description="Path to service account token used by kube auth adapter.",
    )

    @field_validator("vault_verify")
    @classmethod
    def validate_vault_ca(cls, value: Union[bool, str]) -> Union[bool, str]:
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
        ...,
        examples=["server_private_key"],
        description="Base64 encoded server Crypt4GH private key",
    )
    server_public_key: str = Field(
        ...,
        examples=["server_public_key"],
        description="Base64 encoded server Crypt4GH public key",
    )


CONFIG = Config()  # type: ignore [call-arg]
