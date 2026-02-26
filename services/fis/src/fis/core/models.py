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
"""Models for internal representation"""

from typing import Literal

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, Field, SecretBytes, model_validator

FileUploadState = Literal[
    "init",
    "inbox",
    "failed",
    "cancelled",
    "interrogated",
    "awaiting_archival",
    "archived",
]


class BaseFileInformation(BaseModel):
    """Basic file information - all that is needed for interrogation."""

    id: UUID4 = Field(default=..., description="Unique identifier for the file upload")
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    bucket_id: str = Field(
        default=...,
        description="The name of the bucket where the file is currently stored",
    )
    object_id: UUID4 = Field(
        default=..., description="The ID of the file specific to its S3 bucket."
    )
    decrypted_sha256: str = Field(
        default=...,
        description="SHA-256 checksum of the entire unencrypted file content",
    )
    decrypted_size: int = Field(
        default=..., description="The size of the unencrypted file"
    )
    encrypted_size: int = Field(
        default=..., description="The encrypted size of the file before re-encryption"
    )
    part_size: int = Field(
        default=...,
        description="The number of bytes in each file part (last part is likely smaller)",
    )


class FileUnderInterrogation(BaseFileInformation):
    """A user-submitted file upload that needs to be interrogated"""

    state: FileUploadState = Field(
        default="init", description="The state of the FileUpload"
    )
    state_updated: UTCDatetime = Field(
        default=..., description="Timestamp of when state was updated"
    )
    interrogated: bool = Field(
        default=False, description="Indicates whether interrogation has been completed"
    )
    can_remove: bool = Field(
        default=False,
        description="Indicates whether the file can be deleted from the interrogation bucket",
    )


class InterrogationSuccess(BaseModel):
    """Event model informing services that file interrogation succeeded"""

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
    """Event model informing services that file interrogation failed"""

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


class InterrogationReport(BaseModel):
    """Contains the results of file interrogation.

    This is the model stored in the FIS database.
    """

    file_id: UUID4 = Field(
        default=..., description="Unique identifier for the file upload"
    )
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    interrogated_at: UTCDatetime = Field(
        default=..., description="Timestamp showing when interrogation finished"
    )
    passed: bool = Field(..., description="Whether the interrogation was a success")
    bucket_id: str | None = Field(
        default=None,
        description=(
            "The name of the interrogation bucket the file is stored in, if the"
            + " interrogation was successful"
        ),
    )
    object_id: UUID4 | None = Field(
        default=None,
        description=(
            "The ID of the file specific to its S3 bucket, if the interrogation was"
            + " successful."
        ),
    )

    encrypted_parts_md5: list[str] | None = Field(
        default=None, description="Conditional upon success"
    )
    encrypted_parts_sha256: list[str] | None = Field(
        default=None, description="Conditional upon success"
    )
    encrypted_size: int | None = Field(
        default=None,
        description=(
            "The size of the encrypted file content without envelope, if interrogation"
            + " is successful."
        ),
    )
    reason: str | None = Field(
        default=None,
        description="Conditional upon failure, contains reason for failure",
    )


class InterrogationReportWithSecret(InterrogationReport):
    """An InterrogationReport which might contain the file encryption secret.

    This is the model expected by the HTTP API.
    """

    secret: SecretBytes | None = Field(
        default=None, description="Encrypted file encryption secret"
    )

    @model_validator(mode="after")
    def validate_conditional_fields(self) -> "InterrogationReportWithSecret":
        """Validate that conditional fields are set based on passed status."""
        if self.passed:
            for attr in [
                "bucket_id",
                "object_id",
                "encrypted_parts_md5",
                "encrypted_parts_sha256",
                "secret",
                "encrypted_size",
            ]:
                if getattr(self, attr) is None:
                    raise ValueError(f"{attr} must not be None when passed is True")

        elif self.reason is None:
            raise ValueError("reason must not be None when passed is False")
        return self
