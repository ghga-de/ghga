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
#

"""Models used by the API"""

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    EmailStr,
    Field,
    PositiveFloat,
    PositiveInt,
    field_serializer,
)

from .. import __version__

__all__ = ["LoginInfo", "OidcConfiguration", "UserInfo"]


class LoginInfo(BaseModel):
    """Data that is used to login as a user."""

    sub: str | None = Field(default=None, description="subject identifier")
    email: EmailStr | None = Field(
        default=None, description="e-mail address of the user"
    )
    name: str = Field(..., description="the full name of the user")
    valid_seconds: PositiveInt | PositiveFloat | None = Field(
        default=None, description="seconds until the login expires"
    )


class UserInfo(BaseModel):
    """Data that is returned by the UserInfo endpoint."""

    sub: str = Field(..., description="subject identifier")
    email: EmailStr = Field(..., description="e-mail address of the user")
    name: str = Field(..., description="the full name of the user")


class OidcConfiguration(BaseModel):
    """Data that is returned as OpenID Connect configuration."""

    version: str = Field(
        default=__version__, description="Version of the test OpenID Connect Provider"
    )
    issuer: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://op.test"),
        description="URL that the OP asserts as its Issuer Identifier",
    )
    jwks_uri: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://localhost:8080/jwks"),
        description="URL of the OP's JSON Web Key Set document",
    )
    scopes_supported: list[str] = Field(
        default=["openid", "profile", "email"],
        description="List of the OAuth 2.0 scope values that this server supports",
    )
    claims_supported: list[str] = Field(
        default=["sub", "name", "email"],
        description="List of the Claims that the OP can supply values for",
    )
    request_object_signing_alg_values_supported: list[str] = Field(
        default=["ES512"],
        description="List of JWS signing algorithms"
        " supported by the OP for Request Objects",
    )
    userinfo_signing_alg_values_supported: list[str] = Field(
        default=["ES512"],
        description="List of JWS signing algorithms"
        " supported by the OP for the UserInfo endpoint",
    )
    authorization_endpoint: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://localhost:8080/authorize"),
        description="URL of the OP's Authorization Endpoint",
    )
    token_endpoint: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://localhost:8080/token"),
        description="URL of the OP's Token Endpoint",
    )
    userinfo_endpoint: AnyHttpUrl = Field(
        default=AnyHttpUrl("http://localhost:8080/userinfo"),
        description="URL of the OP's UserInfo Endpoint",
    )
    service_documentation: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://github.com/ghga-de/test-oidc-provider"),
        description="URL of a page with information"
        " that developers might need to know when using the OP",
    )

    @field_serializer("issuer")
    def serialize_system(self, system: AnyHttpUrl) -> str:
        """Remove trailing slash from issuer."""
        return str(system).rstrip("/")


class TokenResponse(BaseModel):
    """The data that is returned by the token endpoint."""

    access_token: str = Field(..., description="The issued access token")
    token_type: str = Field(default="Bearer", description="Type of the token")
    expires_in: int = Field(..., description="Lifetime of the access token in seconds")
    scope: str = Field(..., description="The scopes granted")
