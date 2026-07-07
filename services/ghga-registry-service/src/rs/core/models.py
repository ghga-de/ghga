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

from enum import StrEnum
from typing import Annotated, Literal, Self

from ghga_event_schemas.pydantic_ import (
    FileUpload,
    FileUploadBox,
    ResearchDataUploadBox,
    UploadBoxState,
)
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.utils import now_utc_ms_prec
from pydantic import (
    UUID4,
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PositiveInt,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
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
    "DeleteFileBoxWorkOrder",
    "DeleteFileUploadWorkOrder",
    "FileAccession",
    "FileUpload",
    "FileUploadBox",
    "FileUploadWithAccession",
    "GrantAccessRequest",
    "GrantId",
    "GrantWithBoxInfo",
    "ResearchDataUploadBox",
    "ResizeFileBoxWorkOrder",
    "Study",
    "StudyStatus",
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


class FileAccession(BaseModel):
    """A file accession, optionally mapped to an internal file ID and study.

    Persisted via the outbox DAO. Records may exist before a file ID is known
    (unmapped), in which case no outbox event is published.
    """

    pid: PID = Field(..., description="The primary file accession number (primary key)")
    file_id: UUID4 | None = Field(
        default=None,
        description="The corresponding internal file ID, if the accession is mapped",
    )
    study_id: str | None = Field(
        default=None, description="The corresponding study ID, if known"
    )
    created: UTCDatetime = Field(
        default_factory=now_utc_ms_prec,
        description="When the file accession was created",
    )
    mapped: UTCDatetime | None = Field(
        default=None, description="When the file accession was mapped"
    )


# NOTE: StudyStatus and Study are defined here temporarily. They should be moved
# to ghga_event_schemas once the schema is finalized, just like the box and file
# accession models that are already imported from ghga_event_schemas above.
class StudyStatus(StrEnum):
    """All possible states of a Study."""

    DRAFT = "draft"  # study is still editable and in preview mode only
    ARCHIVED = "archived"  # study has been archived and has become immutable


class Study(BaseModel):
    """A study registered in GHGA.

    Persisted via the outbox DAO.
    """

    id: PID = Field(..., description="The PID of the study (primary key)")
    title: str = Field(..., description="Comprehensive title for the study")
    description: str = Field(
        ...,
        description="Detailed description (abstract) describing the goals of the study",
    )
    types: list[str] = Field(
        ..., description="The type(s) of this study (as list of codes)"
    )
    affiliations: list[str] = Field(
        ..., description="The affiliation(s) associated with this study"
    )
    status: StudyStatus = Field(..., description="The current status of the study")
    created: UTCDatetime = Field(
        default_factory=now_utc_ms_prec,
        description="When the entry was first created",
    )
    created_by: UUID4 = Field(
        ..., description="The id of the user who uploaded the study"
    )
    approved: UTCDatetime | None = Field(
        default=None, description="When the study was approved"
    )
    approved_by: UUID4 | None = Field(
        default=None, description="The id of the user who approved the study"
    )
    superseded_by_id: PID | None = Field(
        default=None,
        description="If deprecated, the PID of a newer study superseding this one",
    )
    # Denormalized fields, persisted and updated by business logic:
    has_em: bool = Field(
        default=False, description="Whether the EM has been uploaded already"
    )
    num_datasets: int = Field(
        default=0, description="Number of datasets for this study"
    )
    num_publications: int = Field(
        default=0, description="Number of publications for this study"
    )


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


class ResizeFileBoxWorkOrder(BaseWorkOrderToken):
    """Work order token for resizing a FileUploadBox."""

    work_type: Literal["resize"] = "resize"
    box_id: UUID4 = Field(..., description="ID of the box to resize")


class ViewFileBoxWorkOrder(BaseWorkOrderToken):
    """Work order token for viewing FileUploadBox contents."""

    work_type: Literal["view"] = "view"
    box_id: UUID4 = Field(..., description="ID of the box to view")


class SubmitAccessionMapWorkOrder(BaseWorkOrderToken):
    """Work order token for submitting an accession map."""

    work_type: Literal["map"] = "map"
    user_id: UUID4
    study_id: PID


class DeleteFileUploadWorkOrder(BaseWorkOrderToken):
    """Work order token for deleting a FileUpload."""

    work_type: Literal["delete"] = "delete"
    box_id: UUID4 = Field(..., description="ID of the box containing the file")
    file_id: UUID4 = Field(..., description="ID of the file upload to delete")


class DeleteFileBoxWorkOrder(BaseWorkOrderToken):
    """Work order token for deleting a FileUploadBox and all its files.

    The work type is `"delete_box"` rather than `"delete"` so that a
    `DeleteFileUploadWorkOrder` can't validate as a box-level deletion token.
    """

    work_type: Literal["delete_box"] = "delete_box"
    box_id: UUID4 = Field(..., description="ID of the box to delete")


# API Request/Response models
class CreateUploadBoxRequest(BaseModel):
    """Request model for creating a new research data upload box."""

    title: str = Field(..., description="Short meaningful name for the box")
    description: str = Field(..., description="Describes the upload box in more detail")
    storage_alias: str = Field(..., description="S3 storage alias to use for uploads")
    max_size: PositiveInt = Field(
        ...,
        description=(
            "Maximum number of bytes allowed to be uploaded to the box across all files"
        ),
    )

    @field_validator("title", "description", "storage_alias")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        """Reject strings that are empty or contain only whitespace."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be blank or whitespace-only.")
        return stripped


class CreateUploadBoxResponse(BaseModel):
    """Response model for creating a new research data upload box."""

    box_id: UUID4 = Field(..., description="ID of the newly created upload box")


class UpdateUploadBoxRequest(BaseModel):
    """Request model for updating a research data upload box."""

    version: int = Field(..., description="A counter indicating resource version")
    title: str | None = Field(default=None, description="Updated title")
    description: str | None = Field(default=None, description="Updated description")
    state: UploadBoxState | None = Field(default=None, description="Updated state")
    max_size: PositiveInt | None = Field(
        default=None, description="Updated maximum size in bytes"
    )
    force: bool = Field(
        default=False,
        description="Force the state change even if prerequisites are not met."
        " Only relevant when locking a box; ignored for all other state changes.",
    )

    @model_validator(mode="after")
    def state_and_max_size_are_exclusive(self) -> "Self":
        """Validate that state and max_size are not both set in the same request."""
        if self.state is not None and self.max_size is not None:
            raise ValueError("Cannot update state and max_size in the same request.")
        return self


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
    """A model encapsulating retrieved research data upload boxes and the count
    thereof.
    """

    count: int = Field(..., description="The total number of unpaginated results")
    boxes: list[ResearchDataUploadBox] = Field(
        ..., description="The retrieved research data upload boxes"
    )


class AccessionMapRequest(BaseModel):
    """The request body schema for submitting accession maps"""

    box_version: int = Field(
        default=..., description="A counter indicating research data upload box version"
    )
    mapping: dict[PID, UUID4] = Field(
        default=..., description="Map of accessions to file IDs"
    )
    study_id: PID = Field(
        default=...,
        description="Identifier of the study to which the file accessions belong.",
    )


class FileUploadWithAccession(FileUpload):
    """A FileUpload with its accession"""

    accession: PID | None = Field(
        default=None, description="The accession number assigned to this file."
    )
