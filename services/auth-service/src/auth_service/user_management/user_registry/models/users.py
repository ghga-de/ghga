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

"""User model classes used as DTOs and core entities."""

from enum import Enum
from typing import Optional

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import EmailStr, Field

from . import BaseDto

__all__ = ["User", "UserData", "UserStatus", "StatusChange"]


class UserStatus(str, Enum):
    """User status enum"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class AcademicTitle(str, Enum):
    """Academic title"""

    DR = "Dr."
    PROF = "Prof."


class StatusChange(BaseDto):
    """Details of a status change"""

    previous: Optional[UserStatus] = Field(
        default=None, description="Previous user status"
    )
    by: Optional[str] = Field(
        default=None,
        title="Changed by",
        description="ID of the user who changed the status",
    )
    context: Optional[str] = Field(default=None, description="Status change context")
    change_date: Optional[UTCDatetime] = Field(
        default=None, description="Date of last change"
    )


class UserBasicData(BaseDto):
    """Basic data of a user"""

    name: str = Field(
        default=...,
        description="Full name of the user",
        examples=["Rosalind Franklin"],
    )
    title: Optional[AcademicTitle] = Field(
        default=None, title="Academic title", description="Academic title of the user"
    )
    email: EmailStr = Field(
        default=...,
        description="Preferred e-mail address of the user",
        examples=["user@home.org"],
    )


class UserRegisteredData(UserBasicData):
    """Basic data of a registered user"""

    ext_id: EmailStr = Field(
        default=...,
        title="External ID",
        description="External (Life Science) ID",
        examples=["user@lifescience-ri.eu"],
    )


class UserModifiableData(BaseDto):
    """User data that can be modified"""

    status: Optional[UserStatus] = Field(
        default=None, description="Registration status of the user"
    )
    title: Optional[AcademicTitle] = Field(
        default=None, title="Academic title", description="Academic title of the user"
    )


class UserAutomaticData(BaseDto):
    """User data that is automatically created except the ID"""

    registration_date: UTCDatetime = Field(
        default=..., description="Date when the user was registered"
    )

    status_change: Optional[StatusChange] = Field(
        default=None, description="Last status change"
    )

    active_submissions: list[str] = Field(
        default=[],
        description="List of IDs of all active submissions created by the user",
    )
    active_access_requests: list[str] = Field(
        default=[],
        description="List of IDs of all active data access requests created by the user",
    )


class UserData(UserRegisteredData, UserAutomaticData):
    """User data model without the ID"""

    status: UserStatus = Field(
        default=..., description="Registration status of the user"
    )


class User(UserData):
    """Complete user model with ID"""

    id: str = Field(default=..., description="Internal user ID")  # actually UUID
