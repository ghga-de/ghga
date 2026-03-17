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

"""REST API-specific data models (not used by core package)"""

from typing import Literal, TypeVar

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from ucs.core.models import UploadBoxState


class BoxCreationRequest(BaseModel):
    """Request body for creating a new FileUploadBox."""

    storage_alias: str = Field(
        ..., description="The storage alias to use for this upload box"
    )
    model_config = ConfigDict(title="Box Creation Request")


class BoxUpdateRequest(BaseModel):
    """Request body for updating a FileUploadBox."""

    state: UploadBoxState = Field(default=..., description="Updated state")
    version: int = Field(
        ...,
        description="The expected current version of the box (for optimistic locking)",
    )
    model_config = ConfigDict(title="Box Update Request")


class FileUploadCreationRequest(BaseModel):
    """Request body for creating a new FileUpload."""

    alias: str = Field(
        ...,
        description="The alias for the file within the box (must be unique within the box)",
    )
    decrypted_size: int = Field(
        ..., description="The size of the unencrypted file in bytes", ge=1
    )
    encrypted_size: int = Field(
        ..., description="The size of the encrypted file in bytes", ge=1
    )
    part_size: int = Field(
        ...,
        description="The number of bytes in each file part (last part may be smaller)",
        ge=1,
    )

    @model_validator(mode="after")
    def encrypted_size_exceeds_decrypted_size(self) -> "FileUploadCreationRequest":
        """Ensure encrypted_size is larger than decrypted_size."""
        if self.encrypted_size <= self.decrypted_size:
            raise ValueError(
                f"encrypted_size ({self.encrypted_size}) must be larger than"
                f" decrypted_size ({self.decrypted_size})"
            )
        return self

    model_config = ConfigDict(title="File Upload Creation Request")


class FileUploadCreationResponse(BaseModel):
    """Response body for newly created FileUploads"""

    file_id: UUID4 = Field(
        ..., description="The UUID4 identifier assigned to the FileUpload"
    )
    alias: str = Field(
        ...,
        description="The alias for the file within the box (must be unique within the box)",
    )
    storage_alias: str = Field(
        ..., description="The storage alias to use for this upload"
    )


class FileUploadCompletionRequest(BaseModel):
    """Request body for completing a FileUpload."""

    decrypted_sha256: str = Field(
        ..., description="The checksum of the unencrypted file"
    )
    encrypted_md5: str = Field(
        ...,
        description="The checksum of the encrypted file content, calculated from the list of MD5s for each part.",
    )
    encrypted_parts_md5: list[str] = Field(
        ..., description="The MD5 checksum for each encrypted file part, in sequence"
    )
    encrypted_parts_sha256: list[str] = Field(
        ...,
        description="The SHA-256 checksum for each encrypted file part, in sequence",
    )
    model_config = ConfigDict(title="File Upload Completion Request")


WorkType = Literal[
    "create", "lock", "unlock", "archive", "view", "upload", "close", "delete"
]

T = TypeVar("T", bound=WorkType)


class BaseWorkOrderToken[T: WorkType](BaseModel):
    """Base model pre-configured for use as Dto."""

    work_type: T
    model_config = ConfigDict(frozen=True)


CreateFileBoxWorkOrder = BaseWorkOrderToken[Literal["create"]]


class ChangeFileBoxWorkOrder(BaseWorkOrderToken[Literal["lock", "unlock", "archive"]]):
    """WOT schema authorizing a user to lock or unlock an existing FileUploadBox"""

    box_id: UUID4


class ViewFileBoxWorkOrder(BaseWorkOrderToken[Literal["view"]]):
    """WOT schema authorizing a user to view a FileUploadBox and its FileUploads"""

    box_id: UUID4


class CreateFileWorkOrder(BaseWorkOrderToken[Literal["create"]]):
    """WOT schema authorizing a user to create a new FileUpload"""

    alias: str
    box_id: UUID4


class _FileUploadToken(BaseModel):
    """Partial schema for WOTs authorizing a user to work with existing file uploads.

    This is for existing file uploads only, not for the initiation of new file uploads.
    """

    file_id: UUID4
    box_id: UUID4


class UploadFileWorkOrder(BaseWorkOrderToken[Literal["upload"]], _FileUploadToken):
    """WOT schema authorizing a user to get a file part upload URL"""


class CloseFileWorkOrder(BaseWorkOrderToken[Literal["close"]], _FileUploadToken):
    """WOT schema authorizing a user to complete a file upload"""


class DeleteFileWorkOrder(BaseWorkOrderToken[Literal["delete"]], _FileUploadToken):
    """WOT schema authorizing a user to delete a file upload"""
