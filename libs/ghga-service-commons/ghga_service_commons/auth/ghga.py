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
#


"""GHGA specific authentication and authorization context."""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field

from ghga_service_commons.auth.jwt_auth import JWTAuthConfig, JWTAuthContextProvider
from ghga_service_commons.utils.utc_dates import DateTimeUTC

__all__ = [
    "AcademicTitle",
    "AuthConfig",
    "AuthContext",
    "UserStatus",
    "has_role",
    "is_active",
]


class UserStatus(str, Enum):
    """User status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    INVALID = "invalid"


class AcademicTitle(str, Enum):
    """Academic title"""

    DR = "Dr."
    PROF = "Prof."


class AuthContext(BaseModel):
    """Auth context for all GHGA services."""

    name: str = Field(
        ..., title="Name", description="The full name of the user", example="John Doe"
    )
    email: EmailStr = Field(
        default=...,
        title="E-Mail",
        description="The preferred e-mail address of the user",
        example="user@home.org",
    )
    title: Optional[AcademicTitle] = Field(
        None, title="Title", description="The academic title of the user", example="Dr."
    )
    iat: DateTimeUTC = Field(..., title="Issued at")
    exp: DateTimeUTC = Field(..., title="Expiration time")
    id: Optional[str] = Field(
        None,
        title="Internal ID",
        description="The internal ID of the user (if existing)",
    )
    ext_id: Optional[str] = Field(
        None,
        title="External ID",
        description="The external ID of the user (if required)",
    )
    role: Optional[str] = Field(
        None, title="User role", description="Possible special role of the user in GHGA"
    )
    status: Optional[UserStatus] = Field(
        None,
        title="User status",
        description="The current registration status of the user",
    )


def is_active(context: AuthContext) -> bool:
    """Check whether the given context has an active status."""
    return context.status is UserStatus.ACTIVE


def has_role(context: AuthContext, role: str) -> bool:
    """Check whether the given context is active and has the given role."""
    if not is_active(context):
        return False
    user_role = context.role
    if user_role and "@" not in role:
        user_role = user_role.split("@", 1)[0]
    return role == user_role


class AuthConfig(JWTAuthConfig):
    """Config parameters and their defaults for the example auth context."""

    auth_key: str = Field(
        ...,
        title="Internal public key",
        description="The GHGA internal public key for validating the token signature.",
        example='{"crv": "P-256", "kty": "EC", "x": "...", "y": "..."}',
    )
    auth_algs: list[str] = Field(
        ["ES256"],
        description="A list of all algorithms used for signing GHGA internal tokens.",
    )
    auth_check_claims: dict[str, Any] = Field(
        dict.fromkeys("name email iat exp".split()),
        description="A dict of all GHGA internal claims that shall be verified.",
    )
    auth_map_claims: dict[str, str] = Field(
        {}, description="A mapping of claims to attributes in the GHGA auth context."
    )


GHGAAuthContextProvider = JWTAuthContextProvider[AuthContext]
