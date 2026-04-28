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

"""Core logic for secrets handling"""

import base64
import logging

import crypt4gh.header
from crypt4gh.keys import get_private_key
from ghga_service_commons.utils.crypt import decrypt

from ekss.config import Config
from ekss.ports.inbound.secrets import SecretsHandlerPort
from ekss.ports.outbound.vault import VaultClientPort

log = logging.getLogger(__name__)


class SecretsHandler(SecretsHandlerPort):
    """A class that handles secret deposition in and retrieval from a secure key manager"""

    def __init__(self, config: Config, vault_client: VaultClientPort):
        self._config = config
        self._private_key = get_private_key(
            config.server_private_key_path, lambda: config.private_key_passphrase
        )
        self._vault_client = vault_client

    def get_envelope(self, *, secret_id: str, client_pubkey: bytes) -> bytes:
        """Retrieve the file secret for the given ID and return a Crypt4GH header
        envelope encrypted with the provided client public key.

        Raises:
            SecretRetrievalError: if no secret exists for the given secret_id.
            EnvelopeCreationError: if the envelope cannot be created for the given secret_id.
        """
        try:
            file_secret = self._vault_client.get_secret(key=secret_id)
        except VaultClientPort.SecretRetrievalError as err:
            error = self.SecretRetrievalError(secret_id=secret_id)
            log.error(error, extra={"secret_id": secret_id})
            raise error from err

        try:
            keys = [(0, self._private_key, client_pubkey)]
            header_content = crypt4gh.header.make_packet_data_enc(0, file_secret)
            header_packets = crypt4gh.header.encrypt(header_content, keys)
            header_bytes = crypt4gh.header.serialize(header_packets)
        except Exception as err:
            error = self.EnvelopeCreationError(secret_id=secret_id)
            log.error(
                error, extra={"secret_id": secret_id, "client_pubkey": client_pubkey}
            )
            raise error from err
        return header_bytes

    def deposit_secret(self, *, encrypted_secret: str) -> str:
        """Decrypt the provided Crypt4GH-encrypted file secret and store it in the
        key manager. Returns the secret ID assigned to the stored secret.

        Raises:
            SecretDecryptionError: if the secret cannot be decrypted.
            SecretDecodeError: if the decrypted payload cannot be base64-decoded.
            SecretInsertionError: if the secret cannot be stored.
        """
        try:
            base64_file_secret = decrypt(encrypted_secret, self._private_key)
        except Exception as err:
            error = self.SecretDecryptionError()
            log.error(error)
            raise error from err

        try:
            file_secret = base64.urlsafe_b64decode(base64_file_secret)
        except Exception as err:
            error = self.SecretDecodeError()
            log.error(error)
            raise error from err

        try:
            secret_id = self._vault_client.store_secret(secret=file_secret)
            log.info("Successfully stored secret in Vault")
        except VaultClientPort.SecretInsertionError as err:
            error = self.SecretInsertionError()
            log.error(error)
            raise error from err

        return secret_id

    def delete_secret(self, *, secret_id: str) -> None:
        """Delete the secret associated with the given ID from the key manager.

        Raises:
            SecretRetrievalError: if no secret exists for the given secret_id.
            SecretDeletionError: if the secret with the given ID cannot be deleted.
        """
        try:
            self._vault_client.delete_secret(key=secret_id)
        except VaultClientPort.SecretRetrievalError as err:
            error = self.SecretRetrievalError(secret_id=secret_id)
            log.error(error)
            raise error from err
        except VaultClientPort.SecretDeletionError as err:
            error = self.SecretDeletionError(secret_id=secret_id)
            log.error(error, extra={"secret_id": secret_id})
            raise error from err
