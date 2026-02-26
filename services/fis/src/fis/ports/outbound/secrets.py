# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""SecretsClient port definition"""

from abc import ABC, abstractmethod

from pydantic import SecretBytes


class SecretsClientPort(ABC):
    """A class that interfaces with the Secrets API"""

    class SecretsApiError(RuntimeError):
        """Raised upon failure to deposit or delete a file encryption secret."""

    @abstractmethod
    async def deposit_secret(self, *, secret: SecretBytes) -> str:
        """Deposit an encrypted file encryption secret with the Secrets API"""

    @abstractmethod
    async def delete_secret(self, *, secret_id: str) -> None:
        """Delete a file encryption secret from the Secrets API"""
