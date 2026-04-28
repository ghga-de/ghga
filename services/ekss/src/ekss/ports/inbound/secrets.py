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

"""Port definition for a SecretsHandler"""

from abc import ABC, abstractmethod


class SecretsHandlerPort(ABC):
    """A class that handles secret deposition in and retrieval from a secure key manager"""

    class SecretDecryptionError(Exception):
        """Raised when the encrypted secret cannot be decrypted."""

    class SecretDecodeError(Exception):
        """Raised when a secret payload cannot be base64-decoded."""

    class SecretInsertionError(Exception):
        """Raised when a secret cannot be stored in the key manager."""

    class SecretRetrievalError(Exception):
        """Raised when no secret exists for the given secret ID."""

        def __init__(self, *, secret_id: str):
            super().__init__(f"Failed to retrieve secret with ID: {secret_id}")

    class SecretDeletionError(Exception):
        """Raised when the secret with the given ID cannot be deleted."""

        def __init__(self, *, secret_id: str):
            super().__init__(f"Failed to delete secret with ID: {secret_id}")

    class EnvelopeCreationError(Exception):
        """Raised when a Crypt4GH envelope cannot be created for the given secret ID."""

        def __init__(self, *, secret_id: str):
            super().__init__(
                f"Failed to create envelope for secret with ID: {secret_id}"
            )

    @abstractmethod
    def get_envelope(self, *, secret_id: str, client_pubkey: bytes) -> bytes:
        """Retrieve the file secret for the given ID and return a Crypt4GH header
        envelope encrypted with the provided client public key.

        Raises:
            SecretRetrievalError: if no secret exists for the given secret_id.
            EnvelopeCreationError: if the envelope cannot be created for the given secret_id.
        """

    @abstractmethod
    def deposit_secret(self, *, encrypted_secret: str) -> str:
        """Decrypt the provided Crypt4GH-encrypted file secret and store it in the
        key manager. Returns the secret ID assigned to the stored secret.

        Raises:
            SecretDecryptionError: if the secret cannot be decrypted.
            SecretDecodeError: if the decrypted payload cannot be base64-decoded.
            SecretInsertionError: if the secret cannot be stored.
        """

    @abstractmethod
    def delete_secret(self, *, secret_id: str) -> None:
        """Delete the secret associated with the given ID from the key manager.

        Raises:
            SecretRetrievalError: if no secret exists for the given secret_id.
            SecretDeletionError: if the secret with the given ID cannot be deleted.
        """
