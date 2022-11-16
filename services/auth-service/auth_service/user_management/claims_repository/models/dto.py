# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""DTOs for the claims repository service

Note: we currently use the DTOs also as the core entities.
"""

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator

from ...utils import DateTimeUTC

__all__ = [
    "AuthorityLevel",
    "Claim",
    "ClaimCreation",
    "ClaimFullCreation",
    "ClaimMatch",
    "ClaimUpdate",
    "Condition",
    "Identity",
    "MatchClaim",
    "MatchType",
    "VisaType",
]


class BaseDto(BaseModel):
    """Base model preconfigured for use as Dto."""

    class Config:  # pylint: disable=missing-class-docstring
        frozen = True


class VisaType(str, Enum):
    """Type of a visa"""

    # Standard Visa Types
    AFFILIATION_AND_ROLE = "AffiliationAndRole"
    ACCEPTED_TERMS_AND_POLICIES = "AcceptedTermsAndPolicies"
    RESEARCHER_STATUS = "ResearcherStatus"
    CONTROLLED_ACCESS_GRANTS = "ControlledAccessGrants"
    LINKED_IDENTITIES = "LinkedIdentities"
    # Custom Visa Types
    GHGA_ROLE = "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0"


class AuthorityLevel(str, Enum):
    """Type of asserting authority"""

    SELF = "self"
    PEER = "peer"
    SYSTEM = "system"
    SO = "so"  # signing official
    DAC = "dac"  # data access committee


class MatchClaim(str, Enum):
    """Possible visa claim names for conditions"""

    BY = "by"
    SOURCE = "source"
    VALUE = "value"


class MatchType(str, Enum):
    """Type of matching a claim value"""

    CONST = "const"
    PATTERN = "pattern"
    SPLIT_PATTERN = "split_pattern"


class ClaimMatch(BaseDto):
    """A pair of a claim name and a match value with type"""

    claim: MatchClaim
    match_type: MatchType
    match_value: str


class Condition(BaseDto):
    """A single condition to check a type and a set of claims"""

    type: VisaType
    matches: list[ClaimMatch]


class Identity(BaseDto):
    """A user identity based on an iss/sub pair"""

    iss: HttpUrl = Field(default=..., title="Issuer", description="OpenID Issuer")
    sub: str = Field(default=..., title="Subject", description="OpenID Subject")


# pylint: disable=no-self-argument,no-self-use
class ClaimCreation(BaseDto):
    """A claim made about a user with a user ID"""

    visa_type: str = Field(default=..., title="Visa type", example="AffiliationAndRole")
    visa_value: Union[EmailStr, HttpUrl, list[Identity]] = Field(
        default=...,
        title="Scope of the claim depending of the visa type",
        example="faculty@home.org",
    )

    assertion_date: DateTimeUTC = Field(
        ..., title="Assertion date", example="2022-11-30T12:00:00Z"
    )
    valid_from: DateTimeUTC = Field(
        ..., title="Start date of validity", example="2023-01-01T00:00:00Z"
    )
    valid_until: DateTimeUTC = Field(
        ..., title="End date of validity", example="2023-12-31T23:59:59Z"
    )

    source: HttpUrl = Field(
        ..., title="Asserting organization", example="https://home.org"
    )  # organization making the assertion
    sub_source: Optional[HttpUrl] = Field(
        None, title="Asserting sub-organization", example="https://dac.home.org"
    )  # e.g. DAC or Data Hub
    asserted_by: Optional[AuthorityLevel] = Field(
        None, title="Authority level", example="so"
    )

    conditions: Optional[list[list[Condition]]] = Field(
        None, title="Set of conditions"
    )  # nested list (first level OR, second level AND)

    @validator("valid_until")
    def period_is_valid(cls, value, values):
        """Validate that the dates of the period are in the right order."""
        if "valid_from" in values and value <= values["valid_from"]:
            raise ValueError("'valid_until' must be later than 'valid_from'")
        return value


class ClaimUpdate(BaseDto):
    """A set of attributes that shall be updated in a claim."""

    revocation_date: DateTimeUTC = Field(..., title="Date of revocation")


class ClaimFullCreation(ClaimCreation):
    """A claim about a user with a user ID and all data except the claim ID"""

    user_id: str = Field(  # actually UUID
        default=..., title="ID", description="Internally used ID of the user"
    )

    creation_date: DateTimeUTC = Field(..., title="Date of creation of this claim")
    creation_by: str = Field(..., title="Who created this claim (user ID)")
    revocation_date: Optional[DateTimeUTC] = Field(
        None, title="If revoked, date of revocation"
    )
    revocation_by: Optional[str] = Field(None, title="Who revoked this claim (user ID)")


class Claim(ClaimFullCreation):
    """A claim about a user with a claim ID"""

    id: str = Field(  # actually UUID
        default=..., title="ID", description="Internally used ID of the claim"
    )
