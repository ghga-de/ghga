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
#


"""Fixture for using HashiCorp vault"""

from collections.abc import Generator

import hvac
import hvac.exceptions
from pydantic import BaseModel
from pytest import fixture

from fixtures.config import Config
from fixtures.http_client import HttpClient
from fixtures.state_manager import StateManager


class VaultFixture(StateManager):
    """Fixture for managing Kafka resources."""

    def __init__(self, config: Config, http: HttpClient):
        self.config = config
        self.http = http

    def keys(self) -> list[str]:
        url = f"{self.config.sms_url}/secrets/{self.config.vault_path}"
        response = self.http.get(url, headers=self.auth_headers)
        assert response.status_code == 200, f"Failed to get keys: {response.text}"
        keys = response.json()
        assert isinstance(keys, list), "Keys must be a list"
        return keys

    def empty_secrets(self):
        url = f"{self.config.sms_url}/secrets/{self.config.vault_path}"
        response = self.http.delete(url, headers=self.auth_headers)
        assert response.status_code == 204, f"Failed to delete secrets: {response.text}"


@fixture(name="vault", scope="session")
def vault_fixture(config: Config, http: HttpClient) -> VaultFixture:
    """Pytest fixture for tests using vault."""
    return VaultFixture(config=config, http=http)
