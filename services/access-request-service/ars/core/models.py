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
from pydantic import BaseModel, EmailStr, Field

__all__ = [
    "AccessRequest",
    "AccessRequestCreationData",
    "AccessRequestData",
    "AccessRequestPatchData",
    "AccessRequestStatus",
]


class BaseDto(BaseModel):
    """Base model pre-configured for use as Dto."""

    class Config:  # pylint: disable=missing-class-docstring
        extra = "forbid"
        frozen = True


class AccessRequestStatus(str, Enum):
    """The status of an access request."""

    ALLOWED = "allowed"
    DENIED = "denied"
    PENDING = "pending"


class AccessRequestCreationData(BaseDto):
    """All data necessary to create an access request."""

    user_id: str
    dataset_id: str
    email: EmailStr = Field(
        default=..., description="Contact e-mail address of the requester"
    )
    request_text: str = Field(
        default=..., description="Text note submitted with the request"
    )
    access_starts: DateTimeUTC = Field(
        default=..., description="Requested start date of access"
    )
    access_ends: DateTimeUTC = Field(
        default=..., description="Requested end date of access"
    )


class AccessRequestData(AccessRequestCreationData):
    """All data that describes an access request."""

    full_user_name: str = Field(
        default=...,
        description="The requester's full name including academic title",
    )
    request_created: DateTimeUTC = Field(
        default=..., description="Creation date of the access request"
    )
    status: AccessRequestStatus = Field(
        default=AccessRequestStatus.PENDING,
        description="The status of this access request",
    )
    status_changed: Optional[DateTimeUTC] = Field(
        default=None, description="Last change date of the status of this request"
    )
    changed_by: Optional[str] = Field(
        default=None,
        description="The ID of the data steward who made the status change",
    )


class AccessRequestPatchData(BaseDto):
    """All data that describes an access request patch."""

    status: AccessRequestStatus = Field(
        default=...,
        description="The new status of this access request",
    )


class AccessRequest(AccessRequestData):
    """An access request including a unique identifier."""

    id: str = Field(default=..., description="ID of the access request")
