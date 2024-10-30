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
"""Defines the API of a class that handles requests to interact with a Vault."""

import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class SecretsHandlerPort(ABC):
    """A class to interact with a HashiCorp Vault."""

    @abstractmethod
    def get_secrets(self, vault_path: str) -> list[str]:
        """Returns a list of secrets in the specified vault"""

    @abstractmethod
    def delete_secrets(self, vault_path: str) -> None:
        """Delete all secrets from the specified vault."""
