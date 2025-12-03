# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""IVA model classes used as DTOs and core entities.

An IVA is an "independent verification address" used to verify a user's identity.
"""

from uuid import uuid4

from ghga_event_schemas.pydantic_ import IvaState, IvaType
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, ConfigDict, Field

from . import BaseDto

__all__ = [
    "Iva",
    "IvaAndUserData",
    "IvaBasicData",
    "IvaData",
    "IvaFullData",
    "IvaId",
    "IvaState",
    "IvaType",
    "IvaVerificationCode",
    "IvaWithState",
]


class IvaBasicData(BaseDto):
    """Basic IVA data"""

    type: IvaType = Field(default=..., description="The type of the IVA")
    value: str = Field(default=..., description="The actual validation address")


class IvaWithState(IvaBasicData):
    """Basic IVA data and current state"""

    state: IvaState = Field(
        default=IvaState.UNVERIFIED, description="The state of the IVA"
    )


class IvaVerificationCode(BaseDto):
    """Request and response model containing the verification code for an IVA."""

    verification_code: str = Field(
        default=..., description="The verification code for the IVA"
    )


class IvaInternalData(BaseDto):
    """Internal data of an IVA (not exposed via the API)"""

    user_id: UUID4 = Field(default=..., description="Internal user ID")
    verification_code_hash: str | None = Field(
        default=None, description="Salted hash of the verification code for the IVA"
    )
    verification_attempts: int = Field(
        default=0,
        description="Number of failed verification attempts for the verification code",
    )


class IvaAutomaticData(BaseDto):
    """Data that is automatically added to an IVA"""

    created: UTCDatetime = Field(
        default=..., description="The date and time when the IVA was created"
    )
    changed: UTCDatetime = Field(
        default=..., description="The date and time when the IVA was last changed"
    )


class IvaId(BaseDto):
    """The ID of an IVA"""

    id: UUID4 = Field(default_factory=lambda: uuid4(), description="Internal IVA ID")


class IvaData(IvaId, IvaWithState, IvaAutomaticData):
    """IVA data model with all external data including ID"""

    # this is the model that is exposed via the API
    model_config = ConfigDict(
        title="IVA",
        json_schema_extra={
            "title": "IVA",
            "description": "Independent Verification Address (IVA)",
        },
    )


class IvaAndUserData(IvaData):
    """IVA with all external data and user information."""

    user_id: UUID4 = Field(
        default=..., description="The internal ID of the associated user"
    )
    user_name: str = Field(default=..., description="The full name of the user")
    user_title: str | None = Field(
        default=None, description="The academic title of the user"
    )
    user_email: str = Field(default=..., description="The email address of the user")


class IvaFullData(IvaWithState, IvaInternalData, IvaAutomaticData):
    """IVA data model including all internal data without ID"""


class Iva(IvaId, IvaFullData):
    """IVA data model including internal data and the ID"""
