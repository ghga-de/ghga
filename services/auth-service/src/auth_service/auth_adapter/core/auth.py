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

"""Methods for processing authorization tokens."""

import json
import logging
import time
from functools import cached_property, lru_cache
from typing import Any, NamedTuple, Optional, Union
from urllib.parse import urlparse

import httpx
from fastapi import status
from hexkit.protocols.dao import NoHitsFoundError
from jwcrypto import jwk, jwt
from jwcrypto.common import JWException

from auth_service.config import CONFIG, Config
from auth_service.user_management.claims_repository.core.utils import is_data_steward
from auth_service.user_management.claims_repository.deps import ClaimDao
from auth_service.user_management.user_registry.deps import Depends, UserDao
from auth_service.user_management.user_registry.models.dto import User, UserStatus

from .session_store import Session

__all__ = ["get_user_info", "internal_token_from_session", "jwt_config"]

log = logging.getLogger(__name__)

TIMEOUT = 30  # network timeout in seconds
IAT_LIFETIME = 60 * 60  # validity of internal access token in seconds


class AuthAdapterError(Exception):
    """Auth adapter related error."""


class ConfigurationMissingKey(AuthAdapterError):
    """Missing key in configuration."""


class TokenSigningError(AuthAdapterError):
    """Error when signing JWTs."""


class TokenValidationError(AuthAdapterError):
    """Error when validating JWTs."""


class UserDataMismatchError(AuthAdapterError):
    """Raised when user claims do not match the registered user data."""


class UserInfoError(AuthAdapterError):
    """Error when retrieving data from the userinfo endpoint."""


class ConfigurationDiscoveryError(ConfigurationMissingKey):
    """Raised when configuration is missing and cannot be discovery."""


class OIDCDiscovery:
    """Helper class for using the OIDC discovery mechanism.

    Configuration is only checked and data fetched over the network if needed,
    and all network requests are cached.
    """

    def __init__(self, authority_url: str):
        """Initialize with the authority URL."""
        if not authority_url.endswith("/"):
            authority_url += "/"
        self.authority_url = authority_url

    @property
    def config_url(self) -> str:
        """Get the URL for the configuration."""
        return self.authority_url + ".well-known/openid-configuration"

    @cached_property
    def config(self) -> dict[str, Any]:
        """Fetch the OIDC configuration directory."""
        response = httpx.get(self.config_url, timeout=TIMEOUT)
        try:
            config = response.json()
        except json.JSONDecodeError:
            config = None
        if not isinstance(config, dict) or "version" not in config:
            raise ConfigurationDiscoveryError("Unexpected discovery object")
        return config

    @cached_property
    def issuer(self) -> str:
        """Fetch the issuer from the configuration."""
        issuer = self.config.get("issuer")
        if not issuer:
            raise ConfigurationDiscoveryError("Cannot discover issuer")
        log.info("Discovered issuer: %s", issuer)
        return issuer

    @cached_property
    def jwks_str(self) -> str:
        """Fetch the JSON string with the JWKS."""
        jwks_uri = self.config.get("jwks_uri")
        if not jwks_uri or not isinstance(jwks_uri, str):
            raise ConfigurationDiscoveryError("Cannot discover JWKS URI")
        if not jwks_uri.startswith(self.authority_url):
            raise ConfigurationDiscoveryError("Unexpected JWKS URI")
        log.info("Discovered JWKS URI: %s", jwks_uri)
        jwks_response = httpx.get(jwks_uri, timeout=TIMEOUT)
        try:
            jwks_dict = jwks_response.json()
        except json.JSONDecodeError:
            jwks_dict = None
        if not isinstance(jwks_dict, dict) or "keys" not in jwks_dict:
            raise ConfigurationDiscoveryError("Unexpected JWKS object")
        return jwks_response.text

    @property
    def token_endpoint(self) -> str:
        """Fetch the URL of the token endpoint."""
        token_endpoint = self.config.get("token_endpoint")
        if not token_endpoint or not isinstance(token_endpoint, str):
            raise ConfigurationDiscoveryError("Cannot discover token endpoint")
        log.info("Discovered token endpoint: %s", token_endpoint)
        return token_endpoint

    @property
    def userinfo_endpoint(self) -> str:
        """Fetch the URL of the userinfo endpoint."""
        userinfo_endpoint = self.config.get("userinfo_endpoint")
        if not userinfo_endpoint or not isinstance(userinfo_endpoint, str):
            raise ConfigurationDiscoveryError("Cannot discover userinfo endpoint")
        log.info("Discovered userinfo endpoint: %s", userinfo_endpoint)
        return userinfo_endpoint


class JWTConfig:
    """A container for the JWT related configuration."""

    external_jwks: jwk.JWKSet  # the external public key set
    internal_jwk: jwk.JWK  # the internal key pair
    external_algs: Optional[list[str]] = None  # allowed external signing algorithms
    check_at_claims: dict[str, Any] = {  # access token claims that shall be verified
        "iat": None,
        "exp": None,
        "jti": None,
        "sub": None,
        "token_class": "access_token",
    }
    check_ui_claims: dict[str, Any] = {  # userinfo claims that shall be verified
        "sub": None,
        "name": None,
        "email": None,
    }
    # the claims that are copied from the external access token to the internal token
    copy_at_claims = ("iat", "exp")
    # the claims that are copied from the external userinfo to the internal token
    copy_ui_claims = ("name", "email")
    # the key under which the subject is copied from the external token
    copy_sub_as = "ext_id"
    # the URL of the userinfo endpoint
    userinfo_endpoint: str

    def __init__(self, config: Config = CONFIG) -> None:
        """Load the JWT related configuration parameters."""
        discovery = OIDCDiscovery(str(config.oidc_authority_url))

        external_keys = config.auth_ext_keys
        if not external_keys:
            log.warning("No external signing keys configured, using discovery.")
            external_keys = discovery.jwks_str
        external_jwks = jwk.JWKSet.from_json(external_keys)
        if not any(external_jwk.has_public for external_jwk in external_jwks):
            raise ConfigurationMissingKey("No public external signing keys found.")
        if any(external_jwk.has_private for external_jwk in external_jwks):
            raise ConfigurationMissingKey(
                "Private external signing keys found,"
                " these should not be put in the auth adapter configuration."
            )
        self.external_jwks = external_jwks

        internal_key = config.auth_key
        if not internal_key:
            raise ConfigurationMissingKey("No internal signing keys configured.")
        internal_jwk = jwk.JWK.from_json(internal_key)
        if not internal_jwk.has_private:
            raise ConfigurationMissingKey("No private internal signing keys found.")
        self.internal_jwk = internal_jwk

        external_algs = config.auth_ext_algs
        if external_algs:
            self.external_algs = external_algs
        else:
            log.warning("Allowed external signing algorithms not configured.")
            self.external_algs = None
        authority_url_parts = urlparse(discovery.authority_url)
        if (
            authority_url_parts.scheme == "https"
            and not authority_url_parts.netloc.endswith((".dev", ".test"))
        ):
            # this is a real OP, the issuer should match the authority URL
            issuer = authority_url_parts.scheme + "://" + authority_url_parts.netloc
        else:
            # this is a test OP, discover its issuer, may not match the authority URL
            log.warning("Using issuer from discovery instead of authority URL.")
            issuer = discovery.issuer
        self.check_at_claims["iss"] = issuer
        client_id = config.oidc_client_id
        if client_id:
            self.check_at_claims["client_id"] = client_id
            log.debug("Using OIDC client ID: %s", client_id)
        else:
            log.warning("No OIDC client ID configured.")

        userinfo_endpoint = str(config.oidc_userinfo_endpoint)
        if not userinfo_endpoint:
            log.warning("No external userinfo endpoint configured, using discovery.")
            userinfo_endpoint = str(discovery.userinfo_endpoint)
        self.userinfo_endpoint = userinfo_endpoint


jwt_config = JWTConfig()


@lru_cache(maxsize=1024)
def fetch_user_info(access_token: str) -> dict[str, Any]:
    """Fetch info for the given access token from the userinfo endpoint."""
    response = httpx.get(
        jwt_config.userinfo_endpoint,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if response.status_code != status.HTTP_200_OK:
        raise UserInfoError(f"Cannot request userinfo: {response.reason_phrase}")
    return response.json()


def _user_data_matches(user: User, external_claims: dict[str, Any]) -> bool:
    """Check whether the registered user data matches with the external claims."""
    get = external_claims.get
    return user.name == get("name") and user.email == get("email")


async def exchange_token(
    external_token: str,
    pass_sub: bool = False,
    user_dao: UserDao = Depends(),
    claim_dao: ClaimDao = Depends(),
) -> Optional[str]:
    """Exchange the external token against an internal token.

    If the provided external token is valid, a corresponding internal token
    will be returned.

    The internal token will contain relevant claims from the access token and
    the user info as configured.

    If the user is already registered, the user id, status and title will be
    included in the internal token as well.

    If name or email do not match with the external userinfo, the user status
    will appear as "invalid" in the internal token, but the actual status
    will not  be changed in the user registry.

    If the user is not yet registered, and pass_sub is set, then the sub claim
    will be included in the internal token as "ext_id", otherwise the value None
    will be returned instead of a token.
    If the user has a special internal role, this is passed as the "role"
    claim of the internal token.

    If the external token is invalid, a TokenValidationError is raised.
    If the user info cannot be requested, a UserInfoError is raised.
    If the internal token cannot be signed, a TokenSigningError is raised.
    """
    at_claims = decode_and_validate_token(external_token)
    _assert_at_claims_not_empty(at_claims)
    sub = at_claims["sub"]
    try:
        user = await user_dao.find_one(mapping={"ext_id": sub})
    except NoHitsFoundError:
        # user is not yet registered
        if not pass_sub:
            return None
        user = None
    ui_claims = fetch_user_info(external_token)
    _assert_ui_claims_not_empty(ui_claims)
    if ui_claims["sub"] != sub:
        raise UserInfoError("Subject in userinfo differs from access token.")
    copy_claims = jwt_config.copy_at_claims
    internal_claims = {claim: at_claims[claim] for claim in copy_claims}
    copy_claims = jwt_config.copy_ui_claims
    internal_claims.update({claim: ui_claims[claim] for claim in copy_claims})
    if user:
        # user already exists in the registry
        user_status = (
            user.status if _user_data_matches(user, ui_claims) else UserStatus.INVALID
        )
        internal_claims.update(id=user.id, status=user_status, title=user.title)
        if user_status is UserStatus.ACTIVE and await is_data_steward(
            user.id, user_dao=user_dao, claim_dao=claim_dao
        ):
            internal_claims.update(role="data_steward")
    if pass_sub:
        internal_claims[jwt_config.copy_sub_as] = sub
    return sign_and_encode_token(internal_claims)


def _assert_at_claims_not_empty(at_claims: dict[str, Any]) -> None:
    """Make sure that all important access token claims are not empty.

    Note that JWT.validate() checks only whether claims exist, but we also
    want to make sure that the copied claims are not null or empty strings.

    Raises a TokenValidationError in case one of the claims is empty.
    """
    for claim in jwt_config.check_at_claims:
        if not at_claims[claim]:
            raise TokenValidationError(f"Missing value for {claim} claim.")


def _assert_ui_claims_not_empty(ui_claims: dict[str, Any]) -> None:
    """Make sure that all important user info claims are not empty.

    Raises a UserInfoError in case one of the claims is empty.
    """
    for claim in jwt_config.check_ui_claims:
        if not ui_claims.get(claim):
            raise UserInfoError(f"Missing value for {claim} claim.")


def decode_and_validate_token(
    access_token: str, key: Union[jwk.JWK, jwk.JWKSet] = jwt_config.external_jwks
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
            check_claims=jwt_config.check_at_claims,
            expected_type="JWS",
        )
    except (JWException, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError(f"Not a valid token: {exc}") from exc
    try:
        return json.loads(token.claims)
    except json.JSONDecodeError as exc:
        raise TokenValidationError("Claims cannot be decoded") from exc


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


class UserInfo(NamedTuple):
    """A named tuple for OIDC userinfo claims."""

    sub: str
    name: str
    email: str


def get_user_info(access_token: Optional[str]):
    """Get the user info from the OIDC access token.

    Raises a UserInfoError in case the user info cannot be retrieved.
    """
    if not access_token:
        raise UserInfoError("No access token provided")
    try:
        at_claims = decode_and_validate_token(access_token)
    except TokenValidationError as error:
        raise UserInfoError(f"Access token error: {error}") from error
    _assert_at_claims_not_empty(at_claims)
    ui_claims = fetch_user_info(access_token)
    _assert_ui_claims_not_empty(ui_claims)
    if ui_claims["sub"] != at_claims["sub"]:
        raise UserInfoError("Subject in userinfo differs from access token")
    return UserInfo(ui_claims["sub"], ui_claims["name"], ui_claims["email"])


def internal_token_from_session(session: Session) -> str:
    """Create an internal access token from the given session."""
    issued_at = time.time()
    iat = int(issued_at)
    expires = issued_at + IAT_LIFETIME
    exp = int(expires)
    if exp != expires:
        exp += 1
    claims = {
        "name": session.user_name,
        "email": session.user_email,
        "title": session.user_title,
        "role": session.role,
        "id": session.user_id or session.ext_id,
        "iat": iat,
        "exp": exp,
    }
    return sign_and_encode_token(claims)
