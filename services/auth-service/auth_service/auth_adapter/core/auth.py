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

"""Methods for processing authorization tokens."""

import json
import logging
from typing import Any, Optional

from ghga_service_chassis_lib.utils import now_as_utc
from hexkit.protocols.dao import NoHitsFoundError
from jwcrypto import jwk, jwt
from jwcrypto.common import JWException

from auth_service.config import CONFIG, Config
from auth_service.user_management.claims_repository.core.utils import is_data_steward
from auth_service.user_management.claims_repository.deps import ClaimDao
from auth_service.user_management.user_registry.deps import Depends, UserDao
from auth_service.user_management.user_registry.models.dto import (
    StatusChange,
    User,
    UserStatus,
)

__all__ = ["exchange_token", "jwt_config"]

log = logging.getLogger(__name__)


class AuthAdapterError(Exception):
    """Auth adapter related error."""


class ConfigurationMissingKey(AuthAdapterError):
    """Missing key in configuration"""


class TokenSigningError(AuthAdapterError):
    """Error when signing JWTs."""


class TokenValidationError(AuthAdapterError):
    """Error when validating JWTs."""


class UserDataMismatchError(AuthAdapterError):
    """Raised when user claims do not match the registered user data."""


class JWTConfig:
    """A container for the JWT related configuration."""

    external_jwks: jwk.JWKSet  # the external public key set
    internal_jwk: jwk.JWK  # the internal key pair
    external_algs: Optional[list[str]] = None  # allowed external signing algorithms
    check_claims: dict[str, Any] = {  # claims that shall be verified
        "iat": None,
        "exp": None,
        "jti": None,
        "sub": None,
        "name": None,
        "email": None,
        "token_class": "access_token",
    }
    # the claims that are copied from the external to the internal token
    copied_claims = ("name", "email", "iat", "exp")
    # the key under which the subject is copied from the external token
    copy_sub_as = "ls_id"

    def __init__(self, config: Config = CONFIG) -> None:
        """Load the JWT related configuration parameters."""

        external_keys = config.auth_ext_keys
        if not external_keys:
            raise ConfigurationMissingKey("No external signing keys configured.")
        external_jwks = jwk.JWKSet.from_json(external_keys)
        if not any(external_jwk.has_public for external_jwk in external_jwks):
            raise ConfigurationMissingKey("No public external signing keys found.")
        if any(external_jwk.has_private for external_jwk in external_jwks):
            raise ConfigurationMissingKey(
                "Private external signing keys found,"
                " these should not be put in the auth adapter configuration."
            )
        self.external_jwks = external_jwks

        internal_keys = config.auth_int_keys
        if not internal_keys:
            raise ConfigurationMissingKey("No internal signing keys configured.")
        internal_jwk = jwk.JWK.from_json(internal_keys)
        if not internal_jwk.has_private:
            raise ConfigurationMissingKey("No private internal signing keys found.")
        self.internal_jwk = internal_jwk

        external_algs = config.auth_ext_algs
        if external_algs:
            self.external_algs = external_algs
        else:
            log.warning("Allowed external signing algorithms not configured.")
            self.external_algs = None
        authority_url = config.oidc_authority_url
        if authority_url:
            self.check_claims["iss"] = authority_url
        else:
            log.warning("No OIDC authority URL configured.")
        client_id = config.oidc_client_id
        if client_id:
            self.check_claims["client_id"] = client_id
        else:
            log.warning("No OIDC client ID configured.")


jwt_config = JWTConfig()


def _compare_user_data(user: User, external_claims: dict[str, Any]) -> None:
    """Compare user data and raise an error if there is a mismatch.

    The value of the raised UserDataMismatchError can be used as inactivation context.
    """
    if user.status == UserStatus.ACTIVATED:
        if user.name != external_claims.get("name"):
            raise UserDataMismatchError("name")
        if user.email != external_claims.get("email"):
            raise UserDataMismatchError("email")


def _get_inactivated_user(user: User, context: str) -> User:
    """Get an inactivated copy of the User object."""
    return user.copy(
        update=dict(
            status=UserStatus.INACTIVATED.value,
            status_change=StatusChange(
                previous=user.status,
                by=None,
                context=context,
                change_date=now_as_utc(),
            ),
        )
    )


async def exchange_token(
    external_token: str,
    pass_sub: bool = False,
    user_dao: UserDao = Depends(),
    claim_dao: ClaimDao = Depends(),
) -> Optional[str]:
    """Exchange the external token against an internal token.

    If the provided external token is valid, a corresponding internal token
    will be returned.

    The internal token will contain the name and email taken from the
    external token, and also its issued date and expiry date.
    If the user is already registered, the user id and status will be
    included in the internal token as well.
    If name or email do not match with the external token, the user
    is automatically deactivated in the database and internal token.
    If the user is not yet registered, and pass_sub is set, then the sub claim
    will be included in the internal token as "ls_id", otherwise the value None
    will be returned instead of a token.
    If the user has a special internal role, this is passed as the "role"
    claim of the internal token.

    If the external token is invalid a TokenValidationError is raised.
    If the internal token cannot be signed, a TokenSigningError is raised.
    """
    external_claims = decode_and_validate_token(external_token)
    internal_claims = {
        claim: external_claims[claim] for claim in jwt_config.copied_claims
    }
    sub = external_claims["sub"]
    try:
        user = await user_dao.find_one(mapping={"ls_id": sub})
    except NoHitsFoundError:
        # user is not yet registered
        if not pass_sub:
            return None
    else:
        # user already exists in the registry
        try:
            _compare_user_data(user, external_claims)
        except UserDataMismatchError as mismatch:
            context = f"{mismatch} changed"
            user = _get_inactivated_user(user, context)
            await user_dao.update(user)
        internal_claims.update(id=user.id, status=user.status)
        if user.status is UserStatus.ACTIVATED and await is_data_steward(
            user.id, user_dao=user_dao, claim_dao=claim_dao
        ):
            internal_claims.update(role="data_steward")
    if pass_sub:
        internal_claims[jwt_config.copy_sub_as] = sub
    return sign_and_encode_token(internal_claims)


def _assert_claims_not_empty(claims: dict[str, Any]) -> None:
    """Make sure that all important claims are not empty.

    Note that JWT.validate() checks only whether claims exist, but we also
    want to make sure that the copied claims are not null or empty strings.

    Raises a TokenValidationError in case one of the claims is empty.
    """
    if not claims["sub"]:
        raise TokenValidationError("The subject claim is missing.")
    for claim in jwt_config.copied_claims:
        if not claims[claim]:
            raise TokenValidationError(f"Missing value for {claim} claim.")


def decode_and_validate_token(
    access_token: str, key: jwk.JWKSet = jwt_config.external_jwks
) -> dict[str, Any]:
    """Decode and validate the given JSON Web Token.

    Returns the decoded claims in the token as a dictionary if valid.

    Raises a TokenValidationError in case the token could not be validated.
    """
    if not access_token:
        raise TokenValidationError("Empty token")
    try:
        token = jwt.JWT(
            jwt=access_token,
            key=key,
            algs=jwt_config.external_algs,
            check_claims=jwt_config.check_claims,
            expected_type="JWS",
        )
    except (JWException, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError(f"Not a valid token: {exc}") from exc
    try:
        claims = json.loads(token.claims)
    except json.JSONDecodeError as exc:
        raise TokenValidationError("Claims cannot be decoded") from exc
    _assert_claims_not_empty(claims)
    return claims


def sign_and_encode_token(
    claims: dict[str, Any], key: jwk.JWK = jwt_config.internal_jwk
) -> str:
    """Encode and sign the given payload as JSON Web Token.

    Returns the signed and encoded payload.

    Raises a TokenSigningError in case the payload could not be properly signed.
    """
    if not claims:
        raise TokenSigningError("No payload")
    header = {"alg": "ES256" if key["kty"] == "EC" else "RS256", "typ": "JWT"}
    try:
        token = jwt.JWT(header=header, claims=claims)
        token.make_signed_token(key)
        return token.serialize(compact=True)
    except (JWException, UnicodeEncodeError, KeyError, TypeError, ValueError) as exc:
        raise TokenSigningError(f"Could not sign token: {exc}") from exc
