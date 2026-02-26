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

"""Defines dataclasses for holding business-logic data"""

from typing import Literal

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, ConfigDict, Field

FileUploadState = Literal[
    "init",
    "inbox",
    "failed",
    "cancelled",
    "interrogated",
    "awaiting_archival",
    "archived",
]


class CoreFileMetadata(BaseModel):
    """The core file upload properties"""

    id: UUID4 = Field(default=..., description="Unique identifier for the file upload")
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    bucket_id: str = Field(
        default=...,
        description="The name of the bucket where the file is currently stored",
    )
    object_id: UUID4 = Field(
        ..., description="The ID of the file specific to its S3 bucket."
    )
    decrypted_size: int = Field(..., description="The size of the unencrypted file")
    part_size: int = Field(
        default=...,
        description="The number of bytes in each file part (last part is likely smaller)",
    )


class FileUpload(CoreFileMetadata):
    """Information pertaining to a single given file upload.

    This form of the data might or might not have the following fields populated.
    """

    box_id: UUID4 = Field(
        default=..., description="The ID of the FileUploadBox this file belongs to."
    )
    state: FileUploadState = Field(
        default="init", description="The state of the FileUpload"
    )
    state_updated: UTCDatetime = Field(
        default=..., description="Timestamp of when state was updated"
    )
    secret_id: str | None = Field(
        default=None, description="The ID of the file decryption secret."
    )
    encrypted_size: int | None = Field(
        default=None, description="The encrypted size of the file."
    )
    decrypted_sha256: str | None = Field(
        default=None,
        description="SHA-256 checksum of the entire unencrypted file content",
    )
    encrypted_parts_md5: list[str] | None = Field(
        default=None, description="The MD5 checksum of each encrypted file part"
    )
    encrypted_parts_sha256: list[str] | None = Field(
        default=None, description="The SHA-256 checksum of each encrypted file part"
    )


class ArchivableFileUpload(CoreFileMetadata):
    """A view of a FileUpload event which contains all the information necessary to
    archive a file
    """

    secret_id: str = Field(
        default=..., description="The ID of the file decryption secret."
    )
    encrypted_size: int = Field(
        default=...,
        description="The encrypted size of the file after re-encryption, without envelope.",
    )
    decrypted_sha256: str = Field(
        default=...,
        description="SHA-256 checksum of the entire unencrypted file content",
    )
    encrypted_parts_md5: list[str] = Field(
        default=..., description="The MD5 checksum of each encrypted file part"
    )
    encrypted_parts_sha256: list[str] = Field(
        default=..., description="The SHA-256 checksum of each encrypted file part"
    )


class FileMetadata(ArchivableFileUpload):
    """An ArchivableFileUpload with an archival timestamp"""

    archive_date: UTCDatetime = Field(
        default=..., description="The date and time when this file was archived."
    )


class FileInternallyRegistered(BaseModel):
    """An event schema communicating that a file has been copied into permanent storage.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(..., description="Unique identifier for the file upload")
    archive_date: UTCDatetime = Field(
        ...,
        description="The date and time when this file was archived.",
    )
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    bucket_id: str = Field(
        ..., description="The ID/name of the S3 bucket used to store the file."
    )
    secret_id: str = Field(
        default=..., description="The ID of the file decryption secret."
    )
    decrypted_size: int = Field(..., description="The size of the unencrypted file")
    encrypted_size: int = Field(
        default=..., description="The encrypted size of the file before re-encryption"
    )
    decrypted_sha256: str = Field(
        default=...,
        description="SHA-256 checksum of the entire unencrypted file content",
    )
    encrypted_parts_md5: list[str] = Field(
        default=..., description="The MD5 checksum of each encrypted file part"
    )
    encrypted_parts_sha256: list[str] = Field(
        default=..., description="The SHA-256 checksum of each encrypted file part"
    )
    part_size: int = Field(
        default=...,
        description="The number of bytes in each file part (last part is likely smaller)",
    )


class NonStagedFileRequested(BaseModel):
    """
    This event type is triggered when a user requests to download a file that is not
    yet present in the download bucket and needs to be staged.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(..., description="Unique identifier for the file upload")
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    target_bucket_id: str = Field(
        ...,
        description="The ID of the S3 bucket to which the object should be copied.",
    )
    target_object_id: UUID4 = Field(
        ..., description="The ID to use for the file in the download bucket."
    )
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )
    model_config = ConfigDict(title="non_staged_file_requested")


class FileStagedForDownload(NonStagedFileRequested):
    """This event type is triggered when a file is staged to the download bucket.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    model_config = ConfigDict(title="file_staged_for_download")


class FileDeletionRequested(BaseModel):
    """
    This event is emitted when a request to delete a certain file from the file
    backend has been made.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(..., description="Unique identifier for the file")


class FileDeletionSuccess(FileDeletionRequested):
    """
    This event is emitted when a service has deleted a file from its database as well
    as the S3 buckets it controls.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """
