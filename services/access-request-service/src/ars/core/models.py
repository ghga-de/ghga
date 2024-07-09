# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from enum import Enum
from typing import Annotated

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

__all__ = [
    "AccessRequest",
    "AccessRequestCreationData",
    "AccessRequestData",
    "AccessRequestPatchData",
    "AccessRequestStatus",
]


class BaseDto(BaseModel):
    """Base model pre-configured for use as Dto."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AccessRequestStatus(str, Enum):
    """The status of an access request."""

    ALLOWED = "allowed"
    DENIED = "denied"
    PENDING = "pending"


# Accession format should be moved to the commons module
Accession = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern="^[A-Z]{1,6}[0-9]{3,18}$")
]


class AccessRequestCreationData(BaseDto):
    """All data necessary to create an access request."""

    user_id: str = Field(default=..., description="ID of the user who requests access")
    iva_id: str | None = Field(
        default=None,
        description="ID of the IVA to be used for this request,"
        " but this can also be specified later",
    )
    dataset_id: Accession = Field(
        default=..., description="ID of the dataset for which access is requested"
    )
    email: str = Field(
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


class AccessRequestData(AccessRequestCreationData):
    """All data that describes an access request."""

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
    changed_by: str | None = Field(
        default=None,
        description="The ID of the data steward who made the status change",
    )


class AccessRequestPatchData(BaseDto):
    """All data that describes an access request patch."""

    iva_id: str | None = Field(
        default=None,
        description="ID of the IVA to be used for this request",
    )
    status: AccessRequestStatus = Field(
        default=...,
        description="The new status of this access request",
    )


class AccessRequest(AccessRequestData):
    """An access request including a unique identifier."""

    id: str = Field(default=..., description="ID of the access request")
