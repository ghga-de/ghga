# Copyright 2021 - 2023 Universität Tübingen, DKFZ and EMBL
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

"""
Helper functions for handling authentication and authorization.

These should be eventually made available to all services via a library.
"""

import json
from typing import Any, Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from fastapi.security.base import SecurityBase
from ghga_service_chassis_lib.utils import DateTimeUTC
from jwcrypto import jwk, jwt
from jwcrypto.common import JWException
from pydantic import BaseModel
from starlette.status import HTTP_403_FORBIDDEN

from auth_service.config import CONFIG, Config
from auth_service.user_management.user_registry.models.dto import UserStatus

__all__ = [
    "AuthToken",
    "FetchAuthToken",
    "RequireAuthToken",
    "decode_and_validate_token",
]


class AuthError(Exception):
    """General auth related errors"""


class ConfigurationMissingKey(AuthError):
    """Missing key for auth in configuration"""


class TokenValidationError(AuthError):
    """Error when validating JSON Web Tokens"""


class JWTConfig:
    """A container for the JWT related configuration."""

    internal_jwk: Optional[jwk.JWK] = None  # the internal public key
    internal_algs: list[str] = ["ES256", "RS256"]  # allowed internal signing algorithms
    check_claims: dict[str, Any] = {  # claims that shall be verified
        "name": None,
        "email": None,
        "iat": None,
        "exp": None,
    }

    def __init__(self, config: Config = CONFIG) -> None:
        """Load the JWT related configuration parameters."""

        internal_keys = config.auth_int_keys
        if not internal_keys:
            raise ConfigurationMissingKey("No internal signing keys configured.")
        internal_jwk = jwk.JWK.from_json(internal_keys)
        if not internal_jwk.has_public:
            raise ConfigurationMissingKey("No public internal signing keys found.")
        if internal_jwk.has_private:
            raise ConfigurationMissingKey(
                "Private internal signing keys found,"
                " these should not be put in the user management configuration."
            )
        self.internal_jwk = internal_jwk

        if config.auth_ext_keys:
            raise ConfigurationMissingKey(
                "External signing keys found,"
                " these should not be put in the user management configuration."
            )


jwt_config = JWTConfig()


class AuthToken(BaseModel):
    """Internal auth token."""

    name: str
    email: str
    iat: DateTimeUTC
    exp: DateTimeUTC
    id: Optional[str]
    ls_id: Optional[str]
    role: Optional[str]
    status: Optional[UserStatus]

    def has_role(self, role: str) -> bool:
        """Check whether the user has the given role, no matter w"""
        return (
            self.status == UserStatus.ACTIVATED
            and self.role is not None
            and self.role.split("@", 1)[0] == role
        )


forbidden_error = HTTPException(
    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
)


# All the security utilities that integrate with OpenAPI (and the automatic API docs)
# inherit from SecurityBase, that's how FastAPI knows how to integrate them in OpenAPI.


class FetchAuthToken(SecurityBase):
    """Fetches an optional internal authorization token."""

    def __init__(self):
        """Initialize authorization token fetcher."""
        self.http_bearer = HTTPBearer(auto_error=False)
        self.model = self.http_bearer.model
        self.scheme_name = self.http_bearer.scheme_name

    async def __call__(self, request: Request) -> Optional[AuthToken]:
        """Fetch the token or return None if not available."""
        credentials = await self.http_bearer(request)
        bearer_token = credentials.credentials if credentials else None
        if not bearer_token:
            return None
        try:
            return AuthToken(**decode_and_validate_token(bearer_token))
        except (TokenValidationError, ValueError) as error:
            # raise an error for an invalid token even if it is optional
            raise forbidden_error from error


class RequireAuthToken(SecurityBase):
    """Fetches a required internal authorization token."""

    def __init__(self, activated: bool = True, role: Optional[str] = None):
        """Initialize authorization token fetcher.

        By default, the user must be activated. A role can also be required.
        """
        self.http_bearer = HTTPBearer(auto_error=True)
        self.model = self.http_bearer.model
        self.scheme_name = self.http_bearer.scheme_name
        self.activated = activated
        self.role = role

    async def __call__(self, request: Request) -> AuthToken:
        """Fetch the token or raise an error if not available."""
        credentials = await self.http_bearer(request)
        bearer_token = credentials.credentials if credentials else None
        if not bearer_token:
            raise forbidden_error
        try:
            token = AuthToken(**decode_and_validate_token(bearer_token))
            if self.activated and token.status is not UserStatus.ACTIVATED:
                raise ValueError("User is not activated")
            role = self.role
            if role:
                user_role = token.role
                if user_role and "@" not in role:
                    user_role = user_role.split("@", 1)[0]
                if user_role != role:
                    raise ValueError("User does not have required role")
        except (TokenValidationError, ValueError) as error:
            raise forbidden_error from error
        return token


def decode_and_validate_token(
    token: str, key: jwk.JWK = jwt_config.internal_jwk
) -> dict[str, Any]:
    """Decode and validate the given JSON Web Token.

    Returns the decoded claims in the token as a dictionary if valid.

    Raises a TokenValidationError in case the token could not be validated.
    """
    if not token:
        raise TokenValidationError("Empty token")
    try:
        jwt_token = jwt.JWT(
            jwt=token,
            key=key,
            algs=jwt_config.internal_algs,
            check_claims=jwt_config.check_claims,
            expected_type="JWS",
        )
    except (JWException, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError(f"Not a valid token: {exc}") from exc
    try:
        claims = json.loads(jwt_token.claims)
    except json.JSONDecodeError as exc:
        raise TokenValidationError("Claims cannot be decoded") from exc
    return claims
