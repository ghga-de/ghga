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

"""Data models for the Upload Orchestration Service."""

from typing import Annotated, Literal
from uuid import uuid4

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

UploadBoxState = Literal["open", "locked", "archived"]


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
    """A class representing a FileUploadBox"""

    id: UUID4 = Field(..., description="The ID of the box.")
    version: int = Field(..., description="A counter indicating resource version")
    state: UploadBoxState = Field(..., description="Current state of the box")
    file_count: int = Field(..., description="The number of files in the box")
    size: int = Field(..., description="The total size of all files in the box")
    storage_alias: str = Field(..., description="S3 storage alias to use for uploads")


class BaseWorkOrderToken(BaseModel):
    """Base model for work order tokens."""

    work_type: str
    model_config = ConfigDict(frozen=True)


class CreateFileBoxWorkOrder(BaseWorkOrderToken):
    """Work order token for creating a new FileUploadBox."""

    work_type: Literal["create"] = "create"


class ChangeFileBoxWorkOrder(BaseWorkOrderToken):
    """Work order token for changing FileUploadBox state."""

    work_type: Literal["lock", "unlock", "archive"]
    box_id: UUID4 = Field(..., description="ID of the box to change")


class ViewFileBoxWorkOrder(BaseWorkOrderToken):
    """Work order token for viewing FileUploadBox contents."""

    work_type: Literal["view"] = "view"
    box_id: UUID4 = Field(..., description="ID of the box to view")


# API Request/Response models
class CreateUploadBoxRequest(BaseModel):
    """Request model for creating a new research data upload box."""

    title: str = Field(
        ..., description="Short meaningful name for the box", min_length=1
    )
    description: str = Field(..., description="Describes the upload box in more detail")
    storage_alias: str = Field(
        ..., description="S3 storage alias to use for uploads", min_length=1
    )


class CreateUploadBoxResponse(BaseModel):
    """Response model for creating a new research data upload box."""

    box_id: UUID4 = Field(..., description="ID of the newly created upload box")


class UpdateUploadBoxRequest(BaseModel):
    """Request model for updating a research data upload box."""

    version: int = Field(..., description="A counter indicating resource version")
    title: str | None = Field(default=None, description="Updated title")
    description: str | None = Field(default=None, description="Updated description")
    state: UploadBoxState | None = Field(default=None, description="Updated state")


class GrantAccessRequest(BaseModel):
    """Request model for granting upload access to a user."""

    valid_from: UTCDatetime = Field(..., description="Start date of validity")
    valid_until: UTCDatetime = Field(..., description="End date of validity")
    user_id: UUID4 = Field(..., description="ID of the user to grant access to")
    iva_id: UUID4 = Field(..., description="ID of the IVA verification")
    box_id: UUID4 = Field(..., description="ID of the upload box")

    @field_validator("valid_until")
    @classmethod
    def period_is_valid(cls, value: UTCDatetime, info: ValidationInfo):
        """Validate that the dates of the period are in the right order."""
        data = info.data
        if "valid_from" in data and value <= data["valid_from"]:
            raise ValueError("'valid_until' must be later than 'valid_from'")
        return value


class UploadGrant(BaseModel):
    """An upload access grant."""

    id: UUID4 = Field(..., description="Internal grant ID (same as claim ID)")
    user_id: UUID4 = Field(..., description="Internal user ID")
    iva_id: UUID4 | None = Field(
        default=None, description="ID of an IVA associated with this grant"
    )
    box_id: UUID4 = Field(
        default=..., description="ID of the upload box this grant is for"
    )
    created: UTCDatetime = Field(
        default=..., description="Date of creation of this grant"
    )
    valid_from: UTCDatetime = Field(..., description="Start date of validity")
    valid_until: UTCDatetime = Field(..., description="End date of validity")

    user_name: str = Field(..., description="Full name of the user")
    user_email: EmailStr = Field(
        default=...,
        description="The email address of the user",
    )
    user_title: str | None = Field(
        default=None, description="Academic title of the user"
    )


class GrantWithBoxInfo(UploadGrant):
    """An UploadGrant with the ResearchDataUploadBox title and description."""

    box_title: str = Field(..., description="Short meaningful name for the box")
    box_description: str = Field(
        ..., description="Describes the upload box in more detail"
    )


class BoxRetrievalResults(BaseModel):
    """A model encapsulating retrieved research data upload boxes and the count thereof."""

    count: int = Field(..., description="The total number of unpaginated results")
    boxes: list[ResearchDataUploadBox] = Field(
        ..., description="The retrieved research data upload boxes"
    )


Accession = Annotated[str, StringConstraints(pattern=r"^GHGA.+")]


class AccessionMapRequest(BaseModel):
    """The request body schema for submitting accession maps"""

    version: int = Field(
        ..., description="A counter indicating research data upload box version"
    )
    mapping: dict[Accession, UUID4] = Field(
        default=..., description="Map of accessions to file IDs"
    )


class AccessionMap(BaseModel):
    """A map of file IDs to accession numbers for a box"""

    box_id: UUID4 = Field(..., description="ID of the RDUB this accession map is for")
    mapping: dict[Accession, UUID4] = Field(
        default=..., description="Map of accessions to file IDs"
    )


FileUploadState = Literal[
    "init",
    "inbox",
    "failed",
    "cancelled",
    "interrogated",
    "awaiting_archival",
    "archived",
]


class FileUploadWithAccession(BaseModel):
    """A FileUpload with its accession"""

    id: UUID4 = Field(..., description="Unique identifier for the file upload")
    box_id: UUID4
    alias: str
    state: FileUploadState = Field(
        default="init", description="The state of the FileUpload"
    )
    state_updated: UTCDatetime = Field(
        ..., description="Timestamp of when state was updated"
    )
    storage_alias: str = Field(
        ..., description="The storage alias of the Data Hub housing the file"
    )
    bucket_id: str = Field(
        ..., description="The name of the bucket where the file is currently stored"
    )
    decrypted_sha256: str | None = Field(
        default=None,
        description="SHA-256 checksum of the entire unencrypted file content",
    )
    decrypted_size: int = Field(..., description="The size of the unencrypted file")
    encrypted_size: int | None = Field(
        default=None, description="The encrypted size of the file before re-encryption"
    )
    part_size: int = Field(
        ...,
        description="The number of bytes in each file part (last part is likely smaller)",
    )
    accession: str | None = Field(
        default=None, description="The accession number assigned to this file."
    )
