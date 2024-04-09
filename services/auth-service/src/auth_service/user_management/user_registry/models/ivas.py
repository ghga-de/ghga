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

"""IVA model classes used as DTOs and core entities.

An IVA is an "indendent verification address" used to verify a user's identity.
"""

from enum import Enum
from typing import Optional

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import ConfigDict, Field

from . import BaseDto

__all__ = [
    "IvaType",
    "IvaState",
    "IvaBasicData",
    "IvaWithState",
    "IvaVerificationCode",
    "IvaId",
    "IvaData",
    "IvaFullData",
    "IvaAndUserData",
    "Iva",
]


class IvaType(str, Enum):
    """The type of IVA"""

    PHONE = "Phone"
    FAX = "Fax"
    POSTAL_ADDRESS = "PostalAddress"
    IN_PERSON = "InPerson"


class IvaState(str, Enum):
    """The state of an IVA"""

    UNVERIFIED = "Unverified"
    CODE_REQUESTED = "CodeRequested"
    CODE_CREATED = "CodeCreated"
    CODE_TRANSMITTED = "CodeTransmitted"
    VERIFIED = "Verified"


class IvaBasicData(BaseDto):
    """Basic IVA data"""

    type: IvaType = Field(default=..., description="The type of the IVA")
    value: str = Field(default=..., description="The actual address")


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

    user_id: str = Field(default=..., description="Internal user ID")
    verification_code_hash: Optional[str] = Field(
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

    id: str = Field(default=..., description="Internal IVA ID")  # actually UUID


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

    user_id: str = Field(
        default=..., description="The internal ID of the associated user"
    )
    user_name: str = Field(default=..., description="The full name of the user")
    user_title: Optional[str] = Field(
        default=None, description="The academic title of the user"
    )
    user_email: str = Field(default=..., description="The email address of the user")


class IvaFullData(IvaWithState, IvaInternalData, IvaAutomaticData):
    """IVA data model including all internal data without ID"""


class Iva(IvaId, IvaFullData):
    """IVA data model including internal data and the ID"""
