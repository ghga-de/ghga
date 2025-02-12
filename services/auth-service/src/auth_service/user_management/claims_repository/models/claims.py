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

"""Claims model classes used as DTOs and core entities."""

from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import (
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
    ValidationInfo,
    field_serializer,
    field_validator,
)

from . import BaseDto

__all__ = [
    "Accession",
    "AuthorityLevel",
    "Claim",
    "ClaimCreation",
    "ClaimMatch",
    "ClaimUpdate",
    "ClaimValidity",
    "Condition",
    "Identity",
    "MatchClaim",
    "MatchType",
    "VisaType",
]


# Accession format should be moved to the commons module
Accession = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern="^[A-Z]{1,6}[0-9]{3,18}$")
]


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

    @field_serializer("iss")
    def serialize_system(self, iss: HttpUrl) -> str:
        """Remove trailing slash from issuer."""
        return str(iss).rstrip("/")


class ClaimValidity(BaseDto):
    """Start and end dates for validating claims."""

    valid_from: UTCDatetime = Field(
        default=...,
        description="Start date of validity",
        examples=["2023-01-01T00:00:00Z"],
    )
    valid_until: UTCDatetime = Field(
        default=...,
        description="End date of validity",
        examples=["2023-12-31T23:59:59Z"],
    )

    @field_validator("valid_until")
    @classmethod
    def period_is_valid(cls, value: UTCDatetime, info: ValidationInfo):
        """Validate that the dates of the period are in the right order."""
        data = info.data
        if "valid_from" in data and value <= data["valid_from"]:
            raise ValueError("'valid_until' must be later than 'valid_from'")
        return value


class ClaimCreation(ClaimValidity):
    """A claim made about a user with a user ID"""

    iva_id: str | None = Field(  # actually UUID
        default=None, description="ID of an IVA associated with this claim"
    )

    visa_type: VisaType = Field(default=..., examples=["AffiliationAndRole"])
    visa_value: EmailStr | HttpUrl | list[Identity] = Field(
        default=...,
        description="Scope of the claim depending of the visa type",
        examples=["faculty@home.org"],
    )

    assertion_date: UTCDatetime = Field(
        default=...,
        description="Date when the assertion was made",
        examples=["2022-11-30T12:00:00Z"],
    )

    source: HttpUrl = Field(
        default=..., description="Asserting organization", examples=["https://home.org"]
    )  # organization making the assertion
    sub_source: HttpUrl | None = Field(
        default=None,
        description="Asserting sub-organization",
        examples=["https://dac.home.org"],
    )  # e.g. DAC or Data Hub
    asserted_by: AuthorityLevel | None = Field(
        default=None, description="Authority level", examples=["so", "dac", "system"]
    )

    conditions: list[list[Condition]] | None = Field(
        default=None, description="Set of conditions"
    )  # nested list (first level OR, second level AND)

    @field_serializer("source", "sub_source", "visa_value")
    def serialize_url(self, value: Any) -> str | None:
        """Remove trailing slash from sources without path."""
        if value:
            value = str(value)
            if value.startswith(("http://", "https://")) and value.count("/") == 3:
                value = value.rstrip("/")
        return value


class ClaimUpdate(BaseDto):
    """A set of attributes that shall be updated in a claim."""

    revocation_date: UTCDatetime = Field(default=..., description="Date of revocation")


def new_uuid4() -> str:
    return str(uuid4())


class Claim(ClaimCreation):
    """A claim about a user with a user ID and all data"""

    id: str = Field(  # actually UUID
        default_factory=new_uuid4, description="Internal claim ID"
    )

    user_id: str = Field(  # actually UUID
        default=..., description="Internal user ID"
    )

    creation_date: UTCDatetime = Field(
        default=..., description="Date of creation of this claim"
    )
    revocation_date: UTCDatetime | None = Field(
        default=None, description="If revoked, date of revocation"
    )
