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

from hvac import Client as HvacClient
from hvac.exceptions import InvalidPath
from pydantic import Field
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


class SecretsHandler(SecretsHandlerPort):
    """Adapter wrapping hvac.Client"""

    def __init__(self, config: VaultConfig):
        """Initialized approle based client and login"""
        self._config = config

    @property
    def client(self) -> HvacClient:
        """Return an instance of a vault client"""
        return HvacClient(self._config.vault_url, self._config.vault_token)

    def get_secrets(self, vault_path: str) -> list[str]:
        """Return the IDs of all secrets in the specified vault."""
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
