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

"""Defines dataclasses for business-logic data as well as request/reply models for use
in the API.
"""

from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.protocols.dao import UUID4Field
from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from wps.core.crypt import validate_public_key

__all__ = [
    "BaseWorkOrderToken",
    "BoxWithExpiration",
    "CloseFileWorkOrder",
    "CreateFileWorkOrder",
    "Dataset",
    "DatasetFile",
    "DatasetWithExpiration",
    "DeleteFileWorkOrder",
    "DownloadWorkOrder",
    "FileAccession",
    "FileAccessionMapping",
    "ResearchDataUploadBox",
    "ResearchDataUploadBoxBasics",
    "UploadFileWorkOrder",
    "UploadPathType",
    "UploadWorkOrderTokenRequest",
    "ViewFileBoxWorkOrder",
    "WorkPackage",
    "WorkPackageCreationData",
    "WorkPackageCreationResponse",
    "WorkPackageDetails",
    "WorkPackageType",
    "WorkType",
]

FileAccession = Annotated[str, StringConstraints(pattern=r"^GHGAF.+")]


class BaseDto(BaseModel):
    """Base model pre-configured for use as Dto."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class WorkPackageType(StrEnum):
    """The type of work that a work package describes."""

    DOWNLOAD = "download"
    UPLOAD = "upload"


class DatasetFile(BaseDto):
    """A file as that is part of a dataset."""

    accession: FileAccession = Field(default=..., description="The file accession.")
    extension: str = Field(
        default=..., description="The file extension with a leading dot."
    )


class Dataset(BaseDto):
    """A model describing a dataset."""

    id: str = Field(default=..., description="ID of the dataset")
    stage: WorkPackageType = Field(
        default=..., description="Current stage of this dataset."
    )
    title: str = Field(default=..., description="The title of the dataset.")
    description: str | None = Field(
        default=..., description="The description of the dataset."
    )
    files: list[DatasetFile] = Field(
        default=..., description="Files contained in the dataset."
    )


class DatasetWithExpiration(Dataset):
    """A model describing a dataset with an expiration date."""

    expires: UTCDatetime = Field(
        default=..., description="The expiration date of access to the dataset."
    )


DownloadPathType = Literal["download"]
CreateType = Literal["create"]
UploadType = Literal["upload"]
CloseType = Literal["close"]
DeleteType = Literal["delete"]
ViewType = Literal["view"]
UploadPathType = CreateType | UploadType | CloseType | DeleteType | ViewType
WorkType = UploadPathType | DownloadPathType


class BaseWorkOrderToken(BaseModel):
    """Base model for work order tokens."""

    user_public_crypt4gh_key: str
    model_config = ConfigDict(frozen=True)


class DownloadWorkOrder(BaseWorkOrderToken):
    """WOT schema authorizing a user to download a file from a dataset"""

    work_type: DownloadPathType = "download"
    file_id: UUID4
    accession: FileAccession


class ViewFileBoxWorkOrder(BaseWorkOrderToken):
    """WOT schema authorizing a user to view a FileUploadBox"""

    work_type: ViewType = "view"
    box_id: UUID4


class CreateFileWorkOrder(BaseWorkOrderToken):
    """WOT schema authorizing a user to create a new FileUpload"""

    work_type: CreateType = "create"
    alias: str
    box_id: UUID4


class _FileUploadToken(BaseModel):
    """Partial schema for WOTs authorizing a user to work with existing file uploads.

    This is for existing file uploads only, not for the initiation of new file uploads.
    """

    file_id: UUID4
    box_id: UUID4


class UploadFileWorkOrder(BaseWorkOrderToken, _FileUploadToken):
    """WOT schema authorizing a user to get a file part upload URL"""

    work_type: UploadType = "upload"


class CloseFileWorkOrder(BaseWorkOrderToken, _FileUploadToken):
    """WOT schema authorizing a user to complete a file upload"""

    work_type: CloseType = "close"


class DeleteFileWorkOrder(BaseWorkOrderToken, _FileUploadToken):
    """WOT schema authorizing a user to delete a file upload"""

    work_type: DeleteType = "delete"


class ResearchDataUploadBox(BaseModel):
    """A class representing a ResearchDataUploadBox.

    This will be replaced with the ghga-event-schemas implementation soon.
    """

    id: UUID4 = Field(
        default_factory=uuid4,
        description="Unique identifier for the research data upload box",
    )
    version: int = Field(
        default=..., description="A counter indicating resource version"
    )
    state: Literal["open", "locked", "archived"] = Field(
        default=..., description="Current state of the research data upload box"
    )
    title: str = Field(default=..., description="Short meaningful name for the box")
    description: str = Field(
        default=..., description="Describes the upload box in more detail"
    )
    last_changed: UTCDatetime = Field(
        default=..., description="Timestamp of the latest change"
    )
    changed_by: UUID4 = Field(
        default=..., description="ID of the user who performed the latest change"
    )
    file_upload_box_id: UUID4 = Field(
        default=..., description="The ID of the file upload box."
    )
    file_upload_box_version: int = Field(
        default=..., description="A counter indicating resource version"
    )
    file_upload_box_state: Literal["open", "locked", "archived"] = Field(
        default=..., description="Current state of the file upload box"
    )
    file_count: int = Field(default=0, description="The number of files in the box")
    size: int = Field(default=0, description="The total size of all files in the box")
    storage_alias: str = Field(
        default=..., description="S3 storage alias to use for uploads"
    )


class ResearchDataUploadBoxBasics(BaseDto):
    """A model describing an upload box that groups file uploads.

    This model contains a selected subset of the fields from the shared model
    ResearchDataUploadBox, which is defined in ghga-event-schemas.
    """

    id: UUID4 = Field(
        default=...,
        description="The ID of the full research data upload box."
        + " This is the ID tied to upload claims.",
    )
    file_upload_box_id: UUID4 = Field(
        default=...,
        description="The ID of the file upload box. This is the ID referenced by the Connector.",
    )
    title: str = Field(default=..., description="The title of the upload box.")
    description: str | None = Field(
        default=None, description="The description of the upload box."
    )


class BoxWithExpiration(ResearchDataUploadBoxBasics):
    """A model describing a research data upload box with an expiration date."""

    expires: UTCDatetime = Field(
        default=...,
        description="The expiration date of access to the research data upload box.",
    )


def validate_work_package_data(data):
    """Ensure exactly one of dataset_id or box_id is provided based on work type."""
    errors: list[str] = []
    if data.type == WorkPackageType.DOWNLOAD:
        if not data.dataset_id:
            errors.append("dataset_id is required for download work packages")
        if data.box_id:
            errors.append("box_id shouldn't be provided for download work packages")
    elif data.type == WorkPackageType.UPLOAD:
        if not data.box_id:
            errors.append("box_id is required for upload work packages")
        if data.dataset_id:
            errors.append("dataset_id shouldn't be provided for upload work packages")
    if errors:
        raise ValueError("; ".join(errors))


class WorkPackageCreationData(BaseDto):
    """All data necessary to create a work package."""

    dataset_id: str | None = Field(
        default=None, description="ID of the dataset (for download work packages)"
    )
    box_id: UUID4 | None = Field(
        default=None, description="ID of the upload box (for upload work packages)"
    )
    type: WorkPackageType = Field(default=..., description="The work package type")
    file_ids: list[str] | None = Field(
        default=None,
        description="IDs of all included files."
        " If None, all files of the dataset are assumed as target.",
    )
    user_public_crypt4gh_key: str = Field(
        default=...,
        description="The user's public Crypt4GH key in base64 encoding",
    )

    @field_validator("user_public_crypt4gh_key")
    @classmethod
    def user_public_crypt4gh_key_valid(cls, key: str):
        """Validate the user's public Crypt4GH key."""
        return validate_public_key(key)

    @model_validator(mode="after")
    def validate_ids(self):
        """Ensure exactly one of dataset_id or box_id is provided based on work type."""
        validate_work_package_data(self)
        return self


class WorkPackageCreationResponse(BaseModel):
    """Response when a work package has been created."""

    id: str = Field(default=..., description="ID of the work package")
    token: str = Field(
        default=...,
        description="The work package access token,"
        " encrypted with the user's public Crypt4GH key",
    )
    expires: UTCDatetime = Field(
        default=..., description="The expiration date of the work package access token"
    )


class WorkPackageDetails(BaseModel):
    """Details about the work package that can be requested."""

    type: WorkPackageType = Field(default=..., description="The work package type")
    files: dict[str, str] | None = Field(
        default=None,
        description="IDs of all included files mapped to their file extensions (None"
        + " for upload work packages)",
        examples=[{"GHGAF01": ".json", "GHGAF02": ".csv"}],
    )
    box_id: UUID4 | None = Field(
        default=None, description="ID of the upload box (for upload work packages)"
    )
    created: UTCDatetime = Field(
        default=..., description="Creation date of the work package"
    )
    expires: UTCDatetime = Field(
        default=..., title="Expiration date of the work package"
    )


class WorkPackage(WorkPackageDetails):
    """All data that describes a work package."""

    id: UUID4 = UUID4Field(description="ID of the work package")
    dataset_id: str | None = Field(
        default=None, description="ID of the dataset (for download work packages)"
    )
    box_id: UUID4 | None = Field(
        default=None, description="ID of the upload box (for upload work packages)"
    )
    user_id: UUID4 = Field(default=..., description="The unique ID for the user")
    full_user_name: str = Field(
        default=...,
        description="The user's full name including academic title",
    )
    email: EmailStr = Field(default=..., description="E-Mail address of the user")
    user_public_crypt4gh_key: str = Field(
        default=...,
        description="The user's public Crypt4GH key in base64 encoding",
    )
    token_hash: str = Field(
        default=...,
        description="Hash of the work package access token",
    )

    @model_validator(mode="after")
    def validate_ids(self):
        """Ensure exactly one of dataset_id or box_id is provided based on work type."""
        validate_work_package_data(self)
        return self


class UploadWorkOrderTokenRequest(BaseModel):
    """Request model for creating upload-path work order tokens."""

    work_type: UploadPathType = Field(
        default=..., description="The type of work order token to create"
    )
    alias: str | None = Field(
        default=None, description="File alias (required for CREATE work type)"
    )
    file_id: UUID4 | None = Field(
        default=None,
        description="File ID (required for UPLOAD, CLOSE, DELETE work types)",
    )

    @model_validator(mode="after")
    def validate_parameters_and_work_type(self):
        """Ensure proper params are supplied given work type."""
        if self.work_type == "view":
            return self
        if self.work_type == "create" and not self.alias:
            raise ValueError("File alias is required for CREATE work type")
        elif self.work_type != "create" and not self.file_id:
            raise ValueError("File ID is required for UPLOAD, CLOSE, DELETE work types")
        return self


class FileAccessionMapping(BaseModel):
    """A class used to associate a file ID with an accession number"""

    accession: FileAccession = Field(
        default=..., description="The accession number assigned to this file."
    )
    file_id: UUID4 = Field(
        default=..., description="Unique identifier for the file upload"
    )
