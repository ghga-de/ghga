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
"""Contains a class to serve outbox event data to the core in an idempotent manner."""

from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.mongodb import MongoDbDaoFactory

from ifrs.adapters.inbound import models
from ifrs.adapters.inbound.utils import check_record_is_new, make_record_from_update
from ifrs.adapters.outbound.dao import (
    get_file_deletion_requested_dao,
    get_file_upload_validation_success_dao,
    get_nonstaged_file_requested_dao,
)
from ifrs.config import Config
from ifrs.core.models import FileMetadataBase
from ifrs.ports.inbound.file_registry import FileRegistryPort
from ifrs.ports.inbound.idempotent import IdempotenceHandlerPort
from ifrs.ports.outbound.dao import (
    FileDeletionRequestedDaoPort,
    FileUploadValidationSuccessDaoPort,
    NonStagedFileRequestedDaoPort,
)


async def get_idempotence_handler(
    *,
    config: Config,
    file_registry: FileRegistryPort,
) -> IdempotenceHandlerPort:
    """Get an instance of the IdempotenceHandler."""
    dao_factory = MongoDbDaoFactory(config=config)
    file_deletion_requested_dao = await get_file_deletion_requested_dao(
        dao_factory=dao_factory
    )
    file_upload_validation_success_dao = await get_file_upload_validation_success_dao(
        dao_factory=dao_factory
    )
    nonstaged_file_requested_dao = await get_nonstaged_file_requested_dao(
        dao_factory=dao_factory
    )

    return IdempotenceHandler(
        file_registry=file_registry,
        file_deletion_requested_dao=file_deletion_requested_dao,
        file_upload_validation_success_dao=file_upload_validation_success_dao,
        nonstaged_file_requested_dao=nonstaged_file_requested_dao,
    )


class IdempotenceHandler(IdempotenceHandlerPort):
    """Class to serve outbox event data to the core in an idempotent manner."""

    def __init__(
        self,
        *,
        file_registry: FileRegistryPort,
        nonstaged_file_requested_dao: NonStagedFileRequestedDaoPort,
        file_upload_validation_success_dao: FileUploadValidationSuccessDaoPort,
        file_deletion_requested_dao: FileDeletionRequestedDaoPort,
    ):
        self._file_registry = file_registry
        self._nonstaged_file_requested_dao = nonstaged_file_requested_dao
        self._file_upload_validation_success_dao = file_upload_validation_success_dao
        self._file_deletion_requested_dao = file_deletion_requested_dao

    async def upsert_nonstaged_file_requested(
        self, *, resource_id: str, update: event_schemas.NonStagedFileRequested
    ) -> None:
        """Upsert a NonStagedFileRequested event. Call `stage_registered_file` if the
        idempotence check is passed.

        Args:
            resource_id:
                The resource ID.
            update:
                The NonStagedFileRequested event to upsert.
        """
        record = make_record_from_update(models.NonStagedFileRequestedRecord, update)
        if await check_record_is_new(
            dao=self._nonstaged_file_requested_dao,
            resource_id=resource_id,
            update=update,
            record=record,
        ):
            await self._file_registry.stage_registered_file(
                file_id=resource_id,
                decrypted_sha256=update.decrypted_sha256,
                outbox_object_id=update.target_object_id,
                outbox_bucket_id=update.target_bucket_id,
            )
            await self._nonstaged_file_requested_dao.insert(record)

    async def upsert_file_deletion_requested(
        self, *, resource_id: str, update: event_schemas.FileDeletionRequested
    ) -> None:
        """Upsert a FileDeletionRequested event. Call `delete_file` if the idempotence
        check is passed.

        Args:
            resource_id:
                The resource ID.
            update:
                The FileDeletionRequested event to upsert.
        """
        record = make_record_from_update(models.FileDeletionRequestedRecord, update)
        if await check_record_is_new(
            dao=self._file_deletion_requested_dao,
            resource_id=resource_id,
            update=update,
            record=record,
        ):
            await self._file_registry.delete_file(file_id=resource_id)
            await self._file_deletion_requested_dao.insert(record)

    async def upsert_file_upload_validation_success(
        self, *, resource_id: str, update: event_schemas.FileUploadValidationSuccess
    ) -> None:
        """Upsert a FileUploadValidationSuccess event. Call `register_file` if the
        idempotence check is passed.

        Args:
            resource_id:
                The resource ID.
            update:
                The FileUploadValidationSuccess event to upsert.
        """
        record = make_record_from_update(
            models.FileUploadValidationSuccessRecord, update
        )
        if await check_record_is_new(
            dao=self._file_upload_validation_success_dao,
            resource_id=resource_id,
            update=update,
            record=record,
        ):
            file_without_object_id = FileMetadataBase(
                file_id=update.file_id,
                decrypted_sha256=update.decrypted_sha256,
                decrypted_size=update.decrypted_size,
                upload_date=update.upload_date,
                decryption_secret_id=update.decryption_secret_id,
                encrypted_part_size=update.encrypted_part_size,
                encrypted_parts_md5=update.encrypted_parts_md5,
                encrypted_parts_sha256=update.encrypted_parts_sha256,
                content_offset=update.content_offset,
                storage_alias=update.s3_endpoint_alias,
            )

            await self._file_registry.register_file(
                file_without_object_id=file_without_object_id,
                staging_object_id=update.object_id,
                staging_bucket_id=update.bucket_id,
            )
            await self._file_upload_validation_success_dao.insert(record)
