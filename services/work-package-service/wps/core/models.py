# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
in the API."""

from enum import Enum
from typing import Optional

from ghga_service_commons.utils.utc_dates import DateTimeUTC
from pydantic import BaseModel, EmailStr, Field, validator

from wps.core.crypt import validate_public_key

__all__ = [
    "WorkType",
    "WorkOrderToken",
    "WorkPackageCreationData",
    "WorkPackageCreationResponse",
    "WorkPackageData",
    "WorkPackage",
]


class BaseDto(BaseModel):
    """Base model pre-configured for use as Dto."""

    class Config:  # pylint: disable=missing-class-docstring
        extra = "forbid"
        frozen = True


class DatasetFile(BaseDto):
    """A file as that is part of a dataset."""

    id: str = Field(..., description="The file ID.")
    extension: str = Field(..., description="The file extension with a leading dot.")


class Dataset(BaseDto):
    """A model describing a dataset."""

    id: str = Field(default=..., description="ID of the dataset")
    title: str = Field(default=..., description="The title of the dataset.")
    description: Optional[str] = Field(
        ..., description="The description of the dataset."
    )
    files: list[DatasetFile] = Field(..., description="Files contained in the dataset.")


class WorkType(str, Enum):
    """The type of work that a work package describes."""

    DOWNLOAD = "download"
    UPLOAD = "upload"


class WorkOrderToken(BaseDto):
    """A model describing the payload of a work order token."""

    type: WorkType
    file_id: str
    user_id: str
    user_public_crypt4gh_key: str
    full_user_name: str
    email: EmailStr


class WorkPackageCreationData(BaseDto):
    """All data necessary to create a work package."""

    dataset_id: str
    type: WorkType
    file_ids: Optional[list[str]] = Field(
        default=None,
        description="IDs of all included files."
        " If None, all files of the dataset are assumed as target.",
    )
    user_public_crypt4gh_key: str = Field(
        default=...,
        description="The user's public Crypt4GH key in base64 encoding",
    )

    @validator("user_public_crypt4gh_key")
    def user_public_crypt4gh_key_valid(cls, key):  # pylint: disable=no-self-argument
        """Validate the user's public Crypt4GH key."""
        return validate_public_key(key)


class WorkPackageCreationResponse(BaseModel):
    """Response when a work package has been created."""

    id: str = Field(default=..., description="ID of the work package")
    token: str = Field(
        default=...,
        description="The work package access token,"
        " encrypted with the user's public Crypt4GH key",
    )


class WorkPackageDetails(BaseModel):
    """Details about the work package that can be requested."""

    type: WorkType
    files: dict[str, str] = Field(
        default=...,
        description="IDs of all included files mapped to their file extensions",
        example={"file-id-1": ".json", "file-id-2": ".csv"},
    )
    created: DateTimeUTC = Field(
        default=..., description="Creation date of the work package"
    )
    expires: DateTimeUTC = Field(
        default=..., title="Expiration date of the work package"
    )


class WorkPackageData(WorkPackageDetails):
    """All data that describes a work package."""

    dataset_id: str
    user_id: str
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


class WorkPackage(WorkPackageData):
    """A work package including a unique identifier."""

    id: str = Field(default=..., description="ID of the work package")
