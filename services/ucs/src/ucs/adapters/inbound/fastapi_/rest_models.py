# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from typing import Annotated, Literal, TypeVar

from ghga_event_schemas.pydantic_ import UploadBoxState
from pydantic import (
    UUID4,
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    model_validator,
)

from ucs.constants import MAX_PART_SIZE, MIN_PART_SIZE
from ucs.core.models import FileUpload


def _ensure_valid_sort_fields(sort: str) -> str:
    """Ensure each comma-separated sort spec references a FileUpload field.

    A "-" prefix on a spec (denoting descending order) is ignored for validation.
    An empty string is allowed and means no sort was specified.
    """
    if not sort:
        return sort
    invalid_fields = [
        field_name
        for field_name in (spec.removeprefix("-") for spec in sort.split(","))
        if field_name not in FileUpload.model_fields
    ]
    if invalid_fields:
        raise ValueError(
            f"sort references nonexistent FileUpload fields: {', '.join(invalid_fields)}"
        )
    return sort


SortString = Annotated[str, AfterValidator(_ensure_valid_sort_fields)]


class BoxCreationRequest(BaseModel):
    """Request body for creating a new FileUploadBox."""

    storage_alias: str = Field(
        ..., description="The storage alias to use for this upload box"
    )
    max_size: PositiveInt = Field(
        ...,
        description="Maximum total bytes allowed across all file uploads in this box.",
    )
    model_config = ConfigDict(title="Box Creation Request")


class BoxUpdateRequest(BaseModel):
    """Request body for updating a FileUploadBox."""

    state: UploadBoxState | None = Field(default=None, description="Updated state")
    max_size: PositiveInt | None = Field(
        default=None,
        description="Updated maximum total bytes allowed across all file uploads in this box.",
    )
    version: int = Field(
        ...,
        description="The expected current version of the box (for optimistic locking)",
    )
    force: bool = Field(
        default=False,
        description=(
            "Only applies when locking the box. If True, any uploads still in the"
            " 'init' state will be aborted before locking proceeds."
        ),
    )
    model_config = ConfigDict(title="Box Update Request")

    @model_validator(mode="after")
    def enforce_size_state_exclusivity(self) -> "BoxUpdateRequest":
        """Ensure that one and only one of 'state' or 'max_size' is provided."""
        if self.state is None and self.max_size is None:
            raise ValueError("At least one of 'state' or 'max_size' must be provided.")
        if self.state and self.max_size:
            raise ValueError("Cannot specify state and max_size simultaneously.")
        return self


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
    part_size: PositiveInt = Field(
        ...,
        description="The number of bytes in each file part (last part may be smaller)",
        ge=MIN_PART_SIZE,
        le=MAX_PART_SIZE,
    )
    overwrite: bool = Field(
        default=False,
        description=(
            "If True and a FileUpload for this alias already exists in an active state"
            " (init or inbox), cancel and replace it atomically. Has no effect on"
            " already-failed or already-cancelled uploads."
            " Uploads in interrogated, awaiting_archival, or archived state cannot be"
            " overwritten."
        ),
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
    "create",
    "lock",
    "unlock",
    "archive",
    "resize",
    "view",
    "upload",
    "close",
    "delete",
    "delete_box",
]

T = TypeVar("T", bound=WorkType)


class BaseWorkOrderToken[T: WorkType](BaseModel):
    """Base model pre-configured for use as Dto."""

    work_type: T
    model_config = ConfigDict(frozen=True)


CreateFileBoxWorkOrder = BaseWorkOrderToken[Literal["create"]]


class ChangeFileBoxWorkOrder(
    BaseWorkOrderToken[Literal["lock", "unlock", "archive", "resize"]]
):
    """WOT schema authorizing a user to lock, unlock, archive, or resize a FileUploadBox"""

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


class DeleteFileBoxWorkOrder(BaseWorkOrderToken[Literal["delete_box"]]):
    """WOT schema authorizing the RS to delete a FileUploadBox and all its files.

    The work type is 'delete_box' rather than 'delete' so that a DeleteFileWorkOrder
    (which shares the 'delete' work type and may be signed with the same RS key)
    can never validate as a box-level deletion token.
    """

    box_id: UUID4


class BoxUploadsPage(BaseModel):
    """Paginated response for a box's file uploads."""

    items: list[FileUpload]
    total_count: int
