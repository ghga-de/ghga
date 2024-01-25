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
from ghga_service_commons.utils.utc_dates import UTCDatetime

__all__ = [
    "AcademicTitle",
    "AuthConfig",
    "AuthContext",
    "has_role",
]


class AcademicTitle(str, Enum):
    """Academic title."""

    DR = "Dr."
    PROF = "Prof."


class AuthContext(BaseModel):
    """Auth context for all GHGA services."""

    name: str = Field(
        default=...,
        title="Name",
        description="The full name of the user",
        examples=["John Doe"],
    )
    email: EmailStr = Field(
        default=...,
        title="E-Mail",
        description="The preferred e-mail address of the user",
        examples=["user@home.org"],
    )
    title: Optional[AcademicTitle] = Field(
        default=None,
        title="Title",
        description="The academic title of the user",
        examples=["Dr."],
    )
    iat: UTCDatetime = Field(default=..., title="Issued at")
    exp: UTCDatetime = Field(default=..., title="Expiration time")
    id: str = Field(
        default=...,
        title="User ID",
        description="The internal ID of the authenticated user in GHGA",
    )
    role: Optional[str] = Field(
        default=None,
        title="User role",
        description="Possible special role of the user in GHGA",
    )


def has_role(context: AuthContext, role: str) -> bool:
    """Check whether the user with the given context has the given role."""
    user_role = context.role
    if user_role and "@" not in role:
        user_role = user_role.split("@", 1)[0]
    return role == user_role


class AuthConfig(JWTAuthConfig):
    """Config parameters and their defaults for the example auth context."""

    auth_key: str = Field(
        default=...,
        title="Internal public key",
        description="The GHGA internal public key for validating the token signature.",
        examples=['{"crv": "P-256", "kty": "EC", "x": "...", "y": "..."}'],
    )
    auth_algs: list[str] = Field(
        default=["ES256"],
        description="A list of all algorithms used for signing GHGA internal tokens.",
    )
    auth_check_claims: dict[str, Any] = Field(
        default=dict.fromkeys("id name email iat exp".split()),
        description="A dict of all GHGA internal claims that shall be verified.",
    )
    auth_map_claims: dict[str, str] = Field(
        default={},
        description="A mapping of claims to attributes in the GHGA auth context.",
    )


GHGAAuthContextProvider = JWTAuthContextProvider[AuthContext]
