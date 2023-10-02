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

"""Helper functions for handling JSON Web Tokens and Key Sets."""

import json
from typing import Any

from jwcrypto import jwk, jwt

from .utc_dates import now_as_utc

__all__ = ["generate_jwk"]


def generate_jwk() -> jwk.JWK:
    """Generate a random EC based JWK."""
    return jwk.JWK.generate(kty="EC", crv="P-256")


def sign_and_serialize_token(
    claims: dict[str, Any], key: jwk.JWK, valid_seconds: int = 60 * 10
) -> str:
    """Create a signed JSON Web Token that can be used for testing."""
    header = {"alg": "ES256"}
    iat = int(now_as_utc().timestamp())
    exp = iat + valid_seconds
    claims = {**claims, "iat": iat, "exp": exp}
    token = jwt.JWT(header=header, claims=claims)
    token.make_signed_token(key)
    return token.serialize()


def decode_and_validate_token(token: str, key: jwk.JWK) -> dict[str, Any]:
    """Decode and validate the given JSON Web Token for testing."""
    jwt_token = jwt.JWT(jwt=token, key=key, expected_type="JWS")
    return json.loads(jwt_token.claims)
