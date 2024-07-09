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
#

"""Methods for processing authorization tokens."""

import json
import logging
import time
from functools import cached_property, lru_cache
from typing import Any, NamedTuple

import httpx
from fastapi import Request, status
from jwcrypto import jwk, jwt
from jwcrypto.common import JWException

from auth_service.config import CONFIG, Config

from .session_store import Session

__all__ = ["get_user_info", "internal_token_from_session", "get_jwt_config"]

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
        except json.JSONDecodeError as error:
            log.error("Cannot parse discovery object: %s", error)
            config = None
        if not isinstance(config, dict):
            raise ConfigurationDiscoveryError("Invalid discovery object")
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

    @cached_property
    def token_endpoint(self) -> str:
        """Fetch the URL of the token endpoint."""
        token_endpoint = self.config.get("token_endpoint")
        if not token_endpoint or not isinstance(token_endpoint, str):
            raise ConfigurationDiscoveryError("Cannot discover token endpoint")
        log.info("Discovered token endpoint: %s", token_endpoint)
        return token_endpoint

    @cached_property
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
    external_algs: list[str] | None = None  # allowed external signing algorithms
    check_at_claims: dict[str, Any] = {  # access token claims that shall be verified
        "iat": None,
        "exp": None,
        "jti": None,
        "sub": None,
        "aud": None,
        "scope": None,
    }
    check_ui_claims: dict[str, Any] = {  # userinfo claims that shall be verified
        "sub": None,
        "name": None,
        "email": None,
    }
    # the URL of the userinfo endpoint
    userinfo_endpoint: str

    def __init__(self, config: Config = CONFIG) -> None:
        """Load the JWT related configuration parameters."""
        discovery = OIDCDiscovery(str(config.oidc_authority_url))

        external_keys = config.auth_ext_keys
        if not external_keys:
            log.info("No external signing keys configured, using discovery.")
            external_keys = discovery.jwks_str
        external_jwks = jwk.JWKSet.from_json(external_keys)
        if not any(external_jwk.has_public for external_jwk in external_jwks):
            raise ConfigurationMissingKey("No public external signing keys found.")
        if any(external_jwk.has_private for external_jwk in external_jwks):
            raise ConfigurationMissingKey(
                "Private external signing keys found,"
                " these should not be put in the auth adapter configuration."
            )
        log.debug("Found %d external signing keys", len(external_jwks))
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

        issuer = config.oidc_issuer
        if not issuer:
            log.info("No issuer configured, using discovery.")
        log.debug("Using OIDC issuer: %s", issuer)
        self.check_at_claims["iss"] = issuer

        client_id = config.oidc_client_id
        if client_id:
            self.check_at_claims["client_id"] = client_id
            log.debug("Using OIDC client ID: %s", client_id)
        else:
            log.warning("No OIDC client ID configured.")

        userinfo_endpoint = str(config.oidc_userinfo_endpoint)
        if not userinfo_endpoint:
            log.info("No external userinfo endpoint configured, using discovery.")
            userinfo_endpoint = discovery.userinfo_endpoint
        log.debug("Using OIDC endpoint: %s", userinfo_endpoint)
        self.userinfo_endpoint = userinfo_endpoint


_jwt_config: JWTConfig | None = None


def get_jwt_config() -> JWTConfig:
    """Get the JWT configuration only when required.

    This allows the auth adapter to start even if OIDC discovery fails.
    """
    global _jwt_config
    if _jwt_config is None:
        _jwt_config = JWTConfig()
    return _jwt_config


@lru_cache(maxsize=1024)
def _fetch_user_info(access_token: str) -> dict[str, Any]:
    """Fetch info for the given access token from the userinfo endpoint."""
    response = httpx.get(
        get_jwt_config().userinfo_endpoint,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT,
    )
    if response.status_code != status.HTTP_200_OK:
        raise UserInfoError(f"Cannot request userinfo: {response.reason_phrase}")
    return response.json()


def _assert_at_claims_not_empty(at_claims: dict[str, Any]) -> None:
    """Make sure that all important access token claims are not empty.

    Note that JWT.validate() checks only whether claims exist, but we also
    want to make sure that the copied claims are not null or empty strings.

    Raises a TokenValidationError in case one of the claims is empty.
    """
    for claim in get_jwt_config().check_at_claims:
        if not at_claims[claim]:
            raise TokenValidationError(f"Missing value for {claim} claim.")


def _assert_ui_claims_not_empty(ui_claims: dict[str, Any]) -> None:
    """Make sure that all important user info claims are not empty.

    Raises a UserInfoError in case one of the claims is empty.
    """
    for claim in get_jwt_config().check_ui_claims:
        if not ui_claims.get(claim):
            raise UserInfoError(f"Missing value for {claim} claim.")


def decode_and_validate_token(
    access_token: str, key: jwk.JWK | jwk.JWKSet | None = None
) -> dict[str, Any]:
    """Decode and validate the given JSON Web Token.

    Returns the decoded claims in the token as a dictionary if valid.

    Raises a TokenValidationError in case the token could not be validated.
    """
    if not access_token:
        raise TokenValidationError("Empty token")
    jwt_config = get_jwt_config()
    if not key:
        key = jwt_config.external_jwks
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


def sign_and_encode_token(claims: dict[str, Any], key: jwk.JWK | None = None) -> str:
    """Encode and sign the given payload as JSON Web Token.

    Returns the signed and encoded payload.

    Raises a TokenSigningError in case the payload could not be properly signed.
    """
    if not claims:
        raise TokenSigningError("No payload")
    if not key:
        key = get_jwt_config().internal_jwk
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


def get_user_info(access_token: str | None):
    """Get the user info from the OIDC access token.

    Raises a UserInfoError in case the user info cannot be retrieved.
    """
    if not access_token:
        raise UserInfoError("No access token provided")
    try:
        at_claims = decode_and_validate_token(access_token)
        _assert_at_claims_not_empty(at_claims)
    except TokenValidationError as error:
        raise UserInfoError(f"Access token error: {error}") from error
    ui_claims = _fetch_user_info(access_token)
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


def log_auth_info(request: Request, session: Session) -> None:
    """Log additional authorization info.

    Other info such as timestamp and correlation ID are already
    logged by default using the hexkit logging setup.
    """
    log.info(
        "User authorized",
        extra={
            "method": request.method,
            "path": request.url.path,
            "user": session.user_id,
            "role": session.role,
        },
    )
