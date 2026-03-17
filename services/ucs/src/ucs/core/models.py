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
from uuid import uuid4

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, Field


class S3UploadDetails(BaseModel):
    """Class for linking a multipart upload to its FileUpload object"""

    file_id: UUID4  # the id of the corresponding FileUpload
    bucket_id: str
    object_id: UUID4  # the S3 object ID (from FileUpload.object_id)
    storage_alias: str
    s3_upload_id: str
    initiated: UTCDatetime
    completed: UTCDatetime | None = None


UploadBoxState = Literal["open", "locked", "archived"]

FileUploadState = Literal[
    "init",
    "inbox",
    "failed",
    "cancelled",
    "interrogated",
    "awaiting_archival",
    "archived",
]


class ResearchDataUploadBox(BaseModel):
    """A class representing a ResearchDataUploadBox."""

    id: UUID4 = Field(
        default_factory=uuid4,
        description="Unique identifier for the research data upload box",
    )
    version: int = Field(..., description="A counter indicating resource version")
    state: UploadBoxState = Field(
        ..., description="Current state of the research data upload box"
    )
    title: str = Field(..., description="Short meaningful name for the box")
    description: str = Field(..., description="Describes the upload box in more detail")
    last_changed: UTCDatetime = Field(..., description="Timestamp of the latest change")
    changed_by: UUID4 = Field(
        ..., description="ID of the user who performed the latest change"
    )
    file_upload_box_id: UUID4 = Field(..., description="The ID of the file upload box.")
    file_upload_box_version: int = Field(
        ..., description="A counter indicating resource version"
    )
    file_upload_box_state: UploadBoxState = Field(
        ..., description="Current state of the file upload box"
    )
    file_count: int = Field(default=0, description="The number of files in the box")
    size: int = Field(default=0, description="The total size of all files in the box")
    storage_alias: str = Field(..., description="S3 storage alias to use for uploads")


class FileUploadBox(BaseModel):
    """A class representing a box that bundles files belonging to the same upload."""

    id: UUID4 = Field(..., description="The ID of the box.")
    version: int = Field(..., description="A counter indicating resource version")
    state: UploadBoxState = Field(..., description="Current state of the box")
    file_count: int = Field(..., description="The number of files in the box")
    size: int = Field(..., description="The total size of all files in the box")
    storage_alias: str = Field(..., description="S3 storage alias to use for uploads")


class FileUpload(BaseModel):
    """A FileUpload.

    Contains all information required for a file's journey from upload initiation to
    permanent archival.
    """

    id: UUID4 = Field(default=..., description="Unique identifier for the file upload")
    box_id: UUID4 = Field(
        default=...,
        description="The ID of the FileUploadBox this file is associated with",
    )
    alias: str = Field(
        default=...,
        description="The submitted alias from the metadata (unique within the box)",
    )
    state: FileUploadState = Field(
        default="init", description="The state of the FileUpload"
    )
    state_updated: UTCDatetime = Field(
        default=..., description="Timestamp of when state was updated"
    )
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    bucket_id: str = Field(
        default=...,
        description="The name of the bucket where the file is currently stored",
    )
    object_id: UUID4 = Field(
        default=..., description="The ID of the file specific to its S3 bucket"
    )
    secret_id: str | None = Field(
        default=None,
        description="The internal ID of the Data Hub-generated decryption secret",
    )
    decrypted_size: int = Field(
        default=..., description="The size of the unencrypted file"
    )
    encrypted_size: int = Field(
        default=...,
        description=(
            "The size of the encrypted file content. When the file is in the inbox, this"
            + " includes the Crypt4GH envelope. After re-encryption, the file no longer"
            + " contains an envelope, so the value is slightly smaller."
        ),
    )
    decrypted_sha256: str | None = Field(
        default=None,
        description="SHA-256 checksum of the entire unencrypted file content",
    )
    encrypted_parts_md5: list[str] | None = Field(
        default=None, description="The MD5 checksum for each file part, in sequence"
    )
    encrypted_parts_sha256: list[str] | None = Field(
        default=None, description="The SHA256 checksum for each file part, in sequence"
    )
    part_size: int = Field(
        default=...,
        description="The number of bytes in each file part (last part is likely smaller)",
    )
    failure_reason: str | None = Field(
        default=None,
        description="The reason for upload or interrogation failure, if applicable.",
    )
    inbox_upload_completed: bool = Field(  # TODO: This is a UCS-only field
        default=False,
        description="Indicates whether the file has been completely uploaded to the inbox.",
    )


class InterrogationSuccess(BaseModel):
    """Event model informing services that file interrogation succeeded.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(
        default=..., description="Unique identifier for the file upload"
    )
    secret_id: str | None = Field(
        default=None,
        description="The internal ID of the Data Hub-generated decryption secret",
    )
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    bucket_id: str = Field(
        default=...,
        description="The name of the interrogation bucket the file is stored in",
    )
    object_id: UUID4 = Field(
        default=..., description="The ID of the file specific to its S3 bucket."
    )
    interrogated_at: UTCDatetime = Field(
        default=..., description="Time that the report was generated"
    )
    encrypted_parts_md5: list[str] = Field(
        default=..., description="The MD5 checksum for each file part, in sequence"
    )
    encrypted_parts_sha256: list[str] = Field(
        default=..., description="The SHA256 checksum for each file part, in sequence"
    )
    encrypted_size: int = Field(
        default=...,
        description=("The size of the encrypted file content without envelope."),
    )


class InterrogationFailure(BaseModel):
    """Event model informing services that file interrogation failed.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(
        default=..., description="Unique identifier for the file upload"
    )
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    interrogated_at: UTCDatetime = Field(
        default=..., description="Time that the report was generated"
    )
    reason: str = Field(
        default=...,
        description="The text of the error that caused interrogation to fail",
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
