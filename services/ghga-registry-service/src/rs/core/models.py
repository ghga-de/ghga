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

"""Defines dataclasses for holding business-logic data."""

from typing import Annotated, Literal

from ghga_event_schemas.pydantic_ import (
    FileUpload,
    FileUploadBox,
    ResearchDataUploadBox,
    UploadBoxState,
)
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import (
    UUID4,
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

# Note: shared classes re-exported to avoid importing from ghga_event_schemas everywhere
__all__ = [
    "AccessionMapRequest",
    "BaseWorkOrderToken",
    "BoxRetrievalResults",
    "ChangeFileBoxWorkOrder",
    "CreateFileBoxWorkOrder",
    "CreateUploadBoxRequest",
    "CreateUploadBoxResponse",
    "FileAccession",
    "FileUpload",
    "FileUploadBox",
    "FileUploadWithAccession",
    "GrantAccessRequest",
    "GrantId",
    "GrantWithBoxInfo",
    "ResearchDataUploadBox",
    "SubmitAccessionMapWorkOrder",
    "UpdateUploadBoxRequest",
    "UploadBoxState",
    "UploadGrant",
    "ViewFileBoxWorkOrder",
]


def _ascii_only(v: str) -> str:
    if not v.isascii():
        raise ValueError("must contain only ASCII characters")
    return v


PID = Annotated[
    str, StringConstraints(min_length=1, max_length=256), AfterValidator(_ascii_only)
]

FileAccession = Annotated[str, StringConstraints(pattern=r"^GHGAF.+")]


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


class SubmitAccessionMapWorkOrder(BaseWorkOrderToken):
    """Work order token for submitting an accession map."""

    work_type: Literal["map"] = "map"
    user_id: UUID4
    study_id: PID


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


class GrantId(BaseModel):
    """The ID of an access grant."""

    id: UUID4 = Field(..., description="Internal grant ID (same as claim ID)")


class GrantAccessRequest(BaseModel):
    """Request model for granting upload access to a user."""

    box_id: UUID4 = Field(..., description="ID of the upload box")
    user_id: UUID4 = Field(..., description="ID of the user to grant access to")
    iva_id: UUID4 = Field(..., description="ID of the IVA verification")
    valid_from: UTCDatetime = Field(..., description="Start date of validity")
    valid_until: UTCDatetime = Field(..., description="End date of validity")

    @field_validator("valid_until")
    @classmethod
    def period_is_valid(cls, value: UTCDatetime, info: ValidationInfo):
        """Validate that the dates of the period are in the right order."""
        data = info.data
        if "valid_from" in data and value <= data["valid_from"]:
            raise ValueError("'valid_until' must be later than 'valid_from'")
        return value


class UploadGrant(GrantId):
    """An upload access grant."""

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
    box_state: UploadBoxState = Field(..., description="The state of the upload box")
    box_version: int = Field(..., description="The upload box version")


class BoxRetrievalResults(BaseModel):
    """A model encapsulating retrieved research data upload boxes and the count thereof."""

    count: int = Field(..., description="The total number of unpaginated results")
    boxes: list[ResearchDataUploadBox] = Field(
        ..., description="The retrieved research data upload boxes"
    )


class AccessionMapRequest(BaseModel):
    """The request body schema for submitting accession maps"""

    box_version: int = Field(
        default=..., description="A counter indicating research data upload box version"
    )
    mapping: dict[FileAccession, UUID4] = Field(
        default=..., description="Map of accessions to file IDs"
    )
    study_id: PID = Field(
        default=...,
        description="Identifier of the study to which the file accessions belong.",
    )


class FileUploadWithAccession(FileUpload):
    """A FileUpload with its accession"""

    accession: FileAccession | None = Field(
        default=None, description="The accession number assigned to this file."
    )
