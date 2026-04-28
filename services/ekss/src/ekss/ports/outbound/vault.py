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

"""Port definition for a Vault client class"""

from abc import ABC, abstractmethod


class VaultClientPort(ABC):
    """A class to interface with a Vault-like instance"""

    class VaultException(RuntimeError):
        """Raised when interacting with HashiCorp Vault fails"""

    class SecretInsertionError(VaultException):
        """Raised when a secret cannot be inserted into the vault"""

    class SecretRetrievalError(VaultException):
        """Raised when a secret cannot be retrieved from the vault"""

    class SecretDeletionError(VaultException):
        """Raised when a secret cannot be deleted from the vault"""

    @abstractmethod
    def get_secret(self, *, key: str) -> bytes:
        """Retrieve a secret at the subpath of the given prefix denoted by key.

        Key should be a string returned by store_secret on insertion.

        Raises a VaultException if the secret cannot be retrieved or if the operation
        fails for some unexpected reason.
        """

    @abstractmethod
    def store_secret(self, *, secret: bytes) -> str:
        """Store a secret under a subpath of the given prefix.

        Generates a key to use for the subpath and returns it.

        Raises a VaultException if the secret cannot be stored or if the operation
        fails for some unexpected reason.
        """

    @abstractmethod
    def delete_secret(self, *, key: str) -> None:
        """Delete a secret.

        Raises: SecretDeletionError: if the secret cannot be deleted.
        """
