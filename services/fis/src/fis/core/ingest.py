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
"""Functionality relating to S3 upload metadata processing"""

import json
import logging
from contextlib import suppress
from pathlib import Path

from crypt4gh.keys import get_private_key
from ghga_service_commons.utils.crypt import decrypt
from hexkit.opentelemetry import start_span
from hexkit.protocols.dao import ResourceNotFoundError
from nacl.exceptions import CryptoError
from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings

from fis.core import models
from fis.ports.inbound.ingest import (
    DecryptionError,
    LegacyUploadMetadataProcessorPort,
    UploadMetadataProcessorPort,
    VaultCommunicationError,
    WrongDecryptedFormatError,
)
from fis.ports.outbound.dao import FileDao
from fis.ports.outbound.event_pub import EventPubTranslatorPort
from fis.ports.outbound.vault.client import VaultAdapterPort

log = logging.getLogger(__name__)


class ServiceConfig(BaseSettings):
    """Specific configs for authentication and encryption"""

    private_key_path: Path = Field(
        default=...,
        description="Path to the Crypt4GH private key file of the keypair whose public"
        + " key is used to encrypt the payload.",
    )
    private_key_passphrase: str | None = Field(
        default=None,
        description="Passphrase needed to read the content of the private key file. "
        + "Only needed if the private key is encrypted.",
    )
    token_hashes: list[str] = Field(
        default=...,
        description="List of token hashes corresponding to the tokens that can be used "
        + "to authenticate calls to this service.",
    )


class LegacyUploadMetadataProcessor(LegacyUploadMetadataProcessorPort):
    """Handler for S3 upload metadata processing"""

    def __init__(
        self,
        *,
        config: ServiceConfig,
        vault_adapter: VaultAdapterPort,
        event_publisher: EventPubTranslatorPort,
        file_dao: FileDao,
    ):
        self._config = config
        self._vault_adapter = vault_adapter
        self._event_publisher = event_publisher
        self._file_dao = file_dao

    @start_span()
    async def decrypt_payload(
        self, *, encrypted: models.EncryptedPayload
    ) -> models.LegacyUploadMetadata:
        """Decrypt upload metadata using private key"""
        try:
            private_key = get_private_key(
                self._config.private_key_path,
                callback=lambda: self._config.private_key_passphrase,
            )
            decrypted = decrypt(data=encrypted.payload, key=private_key)
        except (ValueError, CryptoError) as error:
            decrypt_error = DecryptionError()
            log.error(decrypt_error)
            raise decrypt_error from error

        upload_metadata = json.loads(decrypted)

        try:
            return models.LegacyUploadMetadata(**upload_metadata)
        except ValidationError as error:
            format_error = WrongDecryptedFormatError(cause=str(error))
            log.error(format_error)
            raise format_error from error

    async def has_already_been_processed(self, *, file_id: str):
        """Check if file metadata has already been seen and successfully processed."""
        with suppress(ResourceNotFoundError):
            await self._file_dao.get_by_id(file_id)
            return True
        return False

    async def populate_by_event(
        self, *, upload_metadata: models.LegacyUploadMetadata, secret_id: str
    ):
        """Insert File ID into database and publish FileUploadValidationSuccess event."""
        # ID should always be new here because of the has_already_been_processed check.
        await self._file_dao.insert(models.FileIdModel(file_id=upload_metadata.file_id))
        await self._event_publisher.publish_file_interrogation_success(
            secret_id=secret_id,
            upload_metadata=upload_metadata,
        )

    async def store_secret(self, *, file_secret: SecretStr) -> str:
        """Communicate with HashiCorp Vault to store file secret and get secret ID"""
        try:
            return self._vault_adapter.store_secret(secret=file_secret)
        except self._vault_adapter.SecretInsertionError as error:
            comms_error = VaultCommunicationError(message=str(error))
            log.error(comms_error)
            raise comms_error from error


class UploadMetadataProcessor(UploadMetadataProcessorPort):
    """Handler for S3 upload metadata processing"""

    def __init__(
        self,
        *,
        config: ServiceConfig,
        event_publisher: EventPubTranslatorPort,
        vault_adapter: VaultAdapterPort,
        file_dao: FileDao,
    ):
        self._config = config
        self._event_publisher = event_publisher
        self._vault_adapter = vault_adapter
        self._file_dao = file_dao

    @start_span()
    async def decrypt_secret(self, *, encrypted: models.EncryptedPayload) -> SecretStr:
        """Decrypt file secret payload"""
        try:
            private_key = get_private_key(
                self._config.private_key_path,
                callback=lambda: self._config.private_key_passphrase,
            )
            decrypted = SecretStr(decrypt(data=encrypted.payload, key=private_key))
        except (ValueError, CryptoError) as error:
            decrypt_error = DecryptionError()
            raise decrypt_error from error

        return decrypted

    async def has_already_been_processed(self, *, file_id: str):
        """Check if file metadata has already been seen and successfully processed."""
        try:
            await self._file_dao.get_by_id(file_id)
        except ResourceNotFoundError:
            return False
        return True

    async def populate_by_event(
        self, *, upload_metadata: models.UploadMetadata, secret_id: str
    ):
        """Insert File ID into database and publish FileUploadValidationSuccess event."""
        # ID should always be new here because of the has_already_been_processed check.
        await self._file_dao.insert(models.FileIdModel(file_id=upload_metadata.file_id))
        await self._event_publisher.publish_file_interrogation_success(
            secret_id=secret_id,
            upload_metadata=upload_metadata,
        )

    async def store_secret(self, *, file_secret: SecretStr) -> str:
        """Communicate with HashiCorp Vault to store file secret and get secret ID"""
        try:
            return self._vault_adapter.store_secret(secret=file_secret)
        except self._vault_adapter.SecretInsertionError as error:
            comms_error = VaultCommunicationError(message=str(error))
            log.error(comms_error)
            raise comms_error from error
