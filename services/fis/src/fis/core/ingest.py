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
"""Functionality relating to S3 upload metadata processing"""

import json
import logging

from ghga_event_schemas.pydantic_ import FileUploadValidationSuccess
from ghga_service_commons.utils.crypt import decrypt
from ghga_service_commons.utils.utc_dates import now_as_utc
from nacl.exceptions import CryptoError
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings

from fis.core import models
from fis.ports.inbound.ingest import (
    DecryptionError,
    LegacyUploadMetadataProcessorPort,
    UploadMetadataProcessorPort,
    VaultCommunicationError,
    WrongDecryptedFormatError,
)
from fis.ports.outbound.daopub import FileUploadValidationSuccessDao
from fis.ports.outbound.vault.client import VaultAdapterPort

log = logging.getLogger(__name__)


class ServiceConfig(BaseSettings):
    """Specific configs for authentication and encryption"""

    private_key: str = Field(
        default=...,
        description="Base64 encoded private key of the keypair whose public key is used "
        + "to encrypt the payload.",
    )
    token_hashes: list[str] = Field(
        default=...,
        description="List of token hashes corresponding to the tokens that can be used "
        + "to authenticate calls to this service.",
    )


async def _send_file_metadata(
    *,
    dao: FileUploadValidationSuccessDao,
    upload_metadata: models.UploadMetadataBase,
    secret_id: str,
):
    """Send FileUploadValidationSuccess event to downstream services"""
    payload = FileUploadValidationSuccess(
        upload_date=now_as_utc().isoformat(),
        file_id=upload_metadata.file_id,
        object_id=upload_metadata.object_id,
        bucket_id=upload_metadata.bucket_id,
        s3_endpoint_alias=upload_metadata.storage_alias,
        decrypted_size=upload_metadata.unencrypted_size,
        decryption_secret_id=secret_id,
        content_offset=0,
        encrypted_part_size=upload_metadata.part_size,
        encrypted_parts_md5=upload_metadata.encrypted_md5_checksums,
        encrypted_parts_sha256=upload_metadata.encrypted_sha256_checksums,
        decrypted_sha256=upload_metadata.unencrypted_checksum,
    )

    await dao.upsert(payload)


class LegacyUploadMetadataProcessor(LegacyUploadMetadataProcessorPort):
    """Handler for S3 upload metadata processing"""

    def __init__(
        self,
        *,
        config: ServiceConfig,
        file_validation_success_dao: FileUploadValidationSuccessDao,
        vault_adapter: VaultAdapterPort,
    ):
        self._config = config
        self._file_validation_success_dao = file_validation_success_dao
        self._vault_adapter = vault_adapter

    async def decrypt_payload(
        self, *, encrypted: models.EncryptedPayload
    ) -> models.LegacyUploadMetadata:
        """Decrypt upload metadata using private key"""
        try:
            decrypted = decrypt(data=encrypted.payload, key=self._config.private_key)
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

    async def populate_by_event(
        self, *, upload_metadata: models.LegacyUploadMetadata, secret_id: str
    ):
        """Send FileUploadValidationSuccess event to be processed by downstream services"""
        await _send_file_metadata(
            dao=self._file_validation_success_dao,
            secret_id=secret_id,
            upload_metadata=upload_metadata,
        )

    async def store_secret(self, *, file_secret: str) -> str:
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
        file_validation_success_dao: FileUploadValidationSuccessDao,
        vault_adapter: VaultAdapterPort,
    ):
        self._config = config
        self._file_validation_success_dao = file_validation_success_dao
        self._vault_adapter = vault_adapter

    async def decrypt_secret(self, *, encrypted: models.EncryptedPayload) -> str:
        """Decrypt file secret payload"""
        try:
            decrypted = decrypt(data=encrypted.payload, key=self._config.private_key)
        except (ValueError, CryptoError) as error:
            decrypt_error = DecryptionError()
            raise decrypt_error from error

        return decrypted

    async def populate_by_event(
        self, *, upload_metadata: models.UploadMetadata, secret_id: str
    ):
        """Send FileUploadValidationSuccess event to be processed by downstream services"""
        await _send_file_metadata(
            dao=self._file_validation_success_dao,
            secret_id=secret_id,
            upload_metadata=upload_metadata,
        )

    async def store_secret(self, *, file_secret: str) -> str:
        """Communicate with HashiCorp Vault to store file secret and get secret ID"""
        try:
            return self._vault_adapter.store_secret(secret=file_secret)
        except self._vault_adapter.SecretInsertionError as error:
            comms_error = VaultCommunicationError(message=str(error))
            log.error(comms_error)
            raise comms_error from error
