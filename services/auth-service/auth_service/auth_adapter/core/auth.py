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
#

"""Methods for processing authorization tokens."""

import json
import logging
from typing import Any, Optional

from jwcrypto import jwk, jws

from ...config import CONFIG, Config

__all__ = ["exchange_token", "signing_keys"]

log = logging.getLogger(__name__)


class SigningKeys:
    """A container for external and internal signing keys."""

    external_jwks: Optional[jwk.JWKSet] = None  # the external public key set
    internal_jwk: Optional[jwk.JWK] = None  # the internal key pair

    def __init__(self, config: Config = CONFIG) -> None:
        """Load all the signing keys from the configuration."""
        external_keys = config.auth_ext_keys
        try:
            if not external_keys:
                raise ValueError("No external keys configured")
            self.external_jwks = jwk.JWKSet.from_json(external_keys)
        except Exception as exc:  # pylint:disable=broad-except
            # do not throw an error so that the auth adapter can still run
            # even though it will not be able to validate external tokens
            log.error("Error in external signing keys: %s", exc)
        internal_keys = config.auth_int_keys
        try:
            if not internal_keys:
                raise ValueError("No internal signing keys configured.")
            self.internal_jwk = jwk.JWK.from_json(internal_keys)
        except Exception as exc:  # pylint:disable=broad-except
            # do not throw an error so that the auth adapter can still run
            # even though it will not be able to sign internal tokens
            log.error("Error in internal signing key pair: %s", exc)


signing_keys = SigningKeys()


def exchange_token(external_token: Optional[str]) -> Optional[str]:
    """Exchange the external token against an internal token.

    If the provided external token is valid, a corresponding internal token
    will be returned. Otherwise None will be returned.
    """
    payload = decode_and_verify_token(external_token)
    if not payload or not isinstance(payload, dict):
        return None
    name = payload.get("name")
    email = payload.get("email")
    if not (name and email):
        log.debug("Access token does not contain required user info")
        return None
    payload = dict(name=name, email=email)
    internal_token = sign_and_encode_token(payload)
    return internal_token


def decode_and_verify_token(
    access_token: Optional[str], key=None
) -> Optional[dict[str, Any]]:
    """Decode and verify the given JSON Web Token."""
    if not access_token:
        return None
    if not key:
        key = signing_keys.external_jwks
        if not key:
            log.debug("No external signing key, cannot verify token")
            return None
    jws_token = jws.JWS()
    try:
        jws_token.deserialize(access_token, key=key)
        payload = json.loads(jws_token.payload.decode("UTF-8"))
        return payload
    except jws.InvalidJWSObject:
        log.debug("Invalid access token format")
    except jws.InvalidJWSSignature:
        log.debug("Invalid access token signature")
    except jws.JWKeyNotFound:
        log.debug("Signature key for access token not found")
    except UnicodeDecodeError:
        log.debug("Access token payload has invalid encoding")
    except json.JSONDecodeError:
        log.debug("Access token payload is not valid JSON")
    return None


def sign_and_encode_token(payload: dict[str, Any], key=None) -> Optional[str]:
    """Encode and sign the given payload as JSON Web Token.

    Returns None in case the payload could not be properly signed.
    """
    if not payload:
        return None
    if not key:
        key = signing_keys.internal_jwk
        if not key:
            log.debug("No internal signing key, cannot sign token")
            return None
    try:
        jws_token = jws.JWS(json.dumps(payload).encode("utf-8"))
        header = json.dumps({"kid": key.thumbprint()})
        alg = "ES256" if key["kty"] == "EC" else "RS256"
        protected = {"alg": alg}
        jws_token.add_signature(key, alg=alg, protected=protected, header=header)
        token = jws_token.serialize(compact=True)
    except (
        jws.InvalidJWSObject,
        jws.InvalidJWSOperation,
        UnicodeEncodeError,
        ValueError,
    ) as error:
        log.error("Error while signing JTW: %s", error)  # pragma: no cover
        token = None
    return token
