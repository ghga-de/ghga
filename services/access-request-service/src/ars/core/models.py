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

from typing import Annotated
from uuid import uuid4

from ghga_event_schemas.pydantic_ import AccessRequestStatus
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)

__all__ = [
    "AccessRequest",
    "AccessRequestCreationData",
    "AccessRequestPatchData",
    "AccessRequestStatus",
    "Dataset",
]


class BaseDto(BaseModel):
    """Base model pre-configured for use as Dto."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Dataset(BaseDto):
    """Basic information about a dataset."""

    id: str = Field(default=..., description="ID of the dataset")
    title: str = Field(default=..., description="Title of the dataset")
    description: str | None = Field(
        default=None, description="Description of the dataset"
    )
    dac_alias: str = Field(
        default=..., description="The alias of the Data Access Committee"
    )
    dac_email: EmailStr = Field(
        default=..., description="The email address of the Data Access Committee"
    )


# Accession format should be moved to the commons module
Accession = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern="^[A-Z]{1,6}[0-9]{3,18}$")
]


class AccessRequestCreationData(BaseDto):
    """All data necessary to create an access request."""

    user_id: UUID4 = Field(
        default=..., description="ID of the user who requests access"
    )
    iva_id: UUID4 | None = Field(
        default=None,
        description="ID of the IVA to be used for this request,"
        " but this can also be specified later",
    )
    dataset_id: Accession = Field(
        default=..., description="ID of the dataset for which access is requested"
    )
    email: EmailStr = Field(
        default=..., description="Contact e-mail address of the requester"
    )
    request_text: str = Field(
        default=..., description="Text note submitted with the request"
    )
    access_starts: UTCDatetime = Field(
        default=..., description="Requested start date of access"
    )
    access_ends: UTCDatetime = Field(
        default=..., description="Requested end date of access"
    )


class AccessRequest(AccessRequestCreationData):
    """All data that describes an access request."""

    id: UUID4 = Field(default_factory=uuid4, description="ID of the access request")
    dataset_title: str = Field(default=..., description="Title of the dataset")
    dataset_description: str | None = Field(
        default=None, description="Description of the dataset"
    )
    dac_alias: str = Field(
        default=..., description="The alias of the Data Access Committee"
    )
    dac_email: EmailStr = Field(
        default=..., description="The email address of the Data Access Committee"
    )
    full_user_name: str = Field(
        default=...,
        description="The requester's full name including academic title",
    )
    request_created: UTCDatetime = Field(
        default=..., description="Creation date of the access request"
    )
    status: AccessRequestStatus = Field(
        default=AccessRequestStatus.PENDING,
        description="The status of this access request",
    )
    status_changed: UTCDatetime | None = Field(
        default=None, description="Last change date of the status of this request"
    )
    changed_by: UUID4 | None = Field(
        default=None,
        description="The ID of the data steward who made the status change",
    )
    ticket_id: str | None = Field(
        default=None,
        description="The ID of the ticket associated with the access request",
    )
    internal_note: str | None = Field(
        default=None,
        description="A note about the access request only visible to Data Stewards",
    )
    note_to_requester: str | None = Field(
        default=None,
        description="A note about the access request that is visible to the requester",
    )


class AccessRequestPatchData(BaseDto):
    """All data that describes an access request patch."""

    iva_id: UUID4 | None = Field(
        default=None,
        description="ID of the IVA to be used for this request",
    )
    status: AccessRequestStatus | None = Field(
        default=None,
        description="The new status of this access request",
    )
    access_starts: UTCDatetime | None = Field(
        default=None, description="Modified start date of access"
    )
    access_ends: UTCDatetime | None = Field(
        default=None, description="Modified end date of access"
    )
    ticket_id: str | None = Field(
        default=None,
        description="The ID of the ticket associated with the access request",
    )
    internal_note: str | None = Field(
        default=None,
        description="A note about the access request only visible to Data Stewards",
    )
    note_to_requester: str | None = Field(
        default=None,
        description="A note about the access request that is visible to the requester",
    )


class BaseAccessGrant(BaseDto):
    """An access grant based on a corresponding claim with info about the user."""

    id: UUID4 = Field(  # actually UUID
        ..., description="Internal grant ID (same as claim ID)"
    )
    user_id: UUID4 = Field(  # actually UUID
        default=..., description="Internal user ID"
    )
    iva_id: UUID4 | None = Field(  # actually UUID
        default=None, description="ID of an IVA associated with this grant"
    )
    dataset_id: Accession = Field(
        default=..., description="ID of the dataset this grant is for"
    )

    created: UTCDatetime = Field(
        default=..., description="Date of creation of this grant"
    )
    valid_from: UTCDatetime = Field(default=..., description="Start date of validity")
    valid_until: UTCDatetime = Field(default=..., description="End date of validity")

    user_name: str = Field(default=..., description="Full name of the user")
    user_email: EmailStr = Field(
        default=...,
        description="The email address of the user",
    )
    user_title: str | None = Field(
        default=None, description="Academic title of the user"
    )


class AccessGrant(BaseAccessGrant):
    """An access grant with additional info about the dataset."""

    dataset_title: str = Field(default=..., description="Title of the dataset")
    dac_alias: str = Field(
        default=..., description="The alias of the Data Access Committee"
    )
    dac_email: EmailStr = Field(
        default=..., description="The email address of the Data Access Committee"
    )


class GrantValidity(BaseModel):
    """Start and end dates for validating access grants."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid_from: UTCDatetime = Field(
        ..., description="Start date of validity", examples=["2023-01-01T00:00:00Z"]
    )
    valid_until: UTCDatetime = Field(
        ..., description="End date of validity", examples=["2023-12-31T23:59:59Z"]
    )

    @model_validator(mode="after")
    def period_is_valid(self):
        """Validate that the dates of the period are in the right order."""
        if self.valid_until <= self.valid_from:
            raise ValueError("'valid_until' must be later than 'valid_from'")

        return self
