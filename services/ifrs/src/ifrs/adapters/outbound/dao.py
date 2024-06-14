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

"""DAO translators for accessing the database."""

from hexkit.protocols.dao import DaoFactoryProtocol

from ifrs.adapters.inbound import models
from ifrs.core.models import FileMetadata
from ifrs.ports.outbound.dao import (
    FileDeletionRequestedDaoPort,
    FileMetadataDaoPort,
    FileUploadValidationSuccessDaoPort,
    NonStagedFileRequestedDaoPort,
)


async def get_file_metadata_dao(
    *, dao_factory: DaoFactoryProtocol
) -> FileMetadataDaoPort:
    """Setup the DAOs using the specified provider of the DaoFactoryProtocol."""
    return await dao_factory.get_dao(
        name="file_metadata",
        dto_model=FileMetadata,
        id_field="file_id",
    )


async def get_nonstaged_file_requested_dao(
    *, dao_factory: DaoFactoryProtocol
) -> NonStagedFileRequestedDaoPort:
    """Setup the DAOs using the specified provider of the DaoFactoryProtocol."""
    return await dao_factory.get_dao(
        name="nonstaged_file_requested",
        dto_model=models.NonStagedFileRequestedRecord,
        id_field="file_id",
    )


async def get_file_upload_validation_success_dao(
    *, dao_factory: DaoFactoryProtocol
) -> FileUploadValidationSuccessDaoPort:
    """Setup the DAOs using the specified provider of the DaoFactoryProtocol."""
    return await dao_factory.get_dao(
        name="file_upload_validation_success",
        dto_model=models.FileUploadValidationSuccessRecord,
        id_field="file_id",
    )


async def get_file_deletion_requested_dao(
    *, dao_factory: DaoFactoryProtocol
) -> FileDeletionRequestedDaoPort:
    """Setup the DAOs using the specified provider of the DaoFactoryProtocol."""
    return await dao_factory.get_dao(
        name="file_deletion_requested",
        dto_model=models.FileDeletionRequestedRecord,
        id_field="file_id",
    )
