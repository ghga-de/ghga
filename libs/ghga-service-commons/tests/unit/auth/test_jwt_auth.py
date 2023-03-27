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

"""Test the auth.jwt_auth module."""

from datetime import datetime
from enum import Enum
from typing import Any

from jwcrypto import jwk, jwt
from pydantic import BaseModel
from pytest import fixture, mark, raises

from ghga_service_commons.auth.jwt_auth import JWTAuthConfig, JWTAuthContextProvider
from ghga_service_commons.utils.utc_dates import DateTimeUTC, now_as_utc

AUTH_KEY_PAIR = jwk.JWK.generate(kty="RSA", size=2048)


class AuthContext(BaseModel):
    """Auth context for testing."""

    name: str
    subject: str
    issued: DateTimeUTC
    expiry: DateTimeUTC
    admin: bool


class AuthConfig(JWTAuthConfig):
    """Config parameters for testing"""

    auth_key: str = AUTH_KEY_PAIR.export(private_key=False)
    auth_algs: list[str] = ["RS256"]
    auth_check_claims: dict[str, Any] = {
        "name": None,
        "exp": None,
        "iat": None,
        "sub": None,
    }
    auth_map_claims: dict[str, str] = {
        "exp": "expiry",
        "iat": "issued",
        "sub": "subject",
    }


@fixture
def jwt_auth():
    """Get a JWT based auth provider for testing."""
    config = AuthConfig()
    return JWTAuthContextProvider(config=config, context_class=AuthContext)


class TokenModifier(Enum):
    """Modifiers for test tokens."""

    NORMAL = 1
    ADMIN = 2
    EXPIRED = 3
    NO_SUB = 4
    BAD_SUB = 5
    BAD_KEY = 6
    BAD_ALG = 7


def create_token(
    name: str = "John Doe",
    modify: TokenModifier = TokenModifier.NORMAL,
) -> str:
    """Create a valid auth token that can be used for testing."""
    header = {"alg": "RS256"}
    key = AUTH_KEY_PAIR
    if modify is TokenModifier.BAD_KEY:
        key = jwk.JWK.generate(kty="RSA", size=1024)
    elif modify is TokenModifier.BAD_ALG:
        header["alg"] = "ES256"
        key = jwk.JWK.generate(kty="EC", crv="P-256")
    subject = name.lower().replace(" ", "_")
    iat = int(now_as_utc().timestamp())
    if modify is TokenModifier.EXPIRED:
        iat -= 60 * 30  # create an expired token
    exp = iat + 60 * 10  # valid for 10 minutes
    admin = modify is TokenModifier.ADMIN
    claims = {"name": name, "sub": subject, "iat": iat, "exp": exp, "admin": admin}
    if modify is TokenModifier.NO_SUB:
        del claims["sub"]
    elif modify is TokenModifier.BAD_SUB:
        claims["sub"] = 42
    token = jwt.JWT(header=header, claims=claims)
    token.make_signed_token(key)
    return token.serialize()


@mark.asyncio
async def test_valid_context(jwt_auth):
    """Test getting a valid auth context."""
    token = create_token()
    context = await jwt_auth.get_context(token)
    assert isinstance(context, AuthContext)
    assert context.name == "John Doe"
    assert context.subject == "john_doe"
    assert context.admin is False
    assert isinstance(context.issued, datetime)
    assert isinstance(context.expiry, datetime)
    assert str(context.expiry - context.issued) == "0:10:00"


@mark.asyncio
async def test_admin_context(jwt_auth):
    """Test getting a valid auth context for an admin."""
    token = create_token("Jane Roe", TokenModifier.ADMIN)
    context = await jwt_auth.get_context(token)
    assert isinstance(context, AuthContext)
    assert context.name == "Jane Roe"
    assert context.subject == "jane_roe"
    assert context.admin is True
    assert isinstance(context.issued, datetime)
    assert isinstance(context.expiry, datetime)
    assert str(context.expiry - context.issued) == "0:10:00"


@mark.asyncio
async def test_empty_token(jwt_auth):
    """Test getting a auth context with empty token."""
    expected_error = jwt_auth.AuthContextValidationError
    expected_message = "Empty token"
    with raises(expected_error, match=expected_message):
        await jwt_auth.get_context("")


@mark.asyncio
async def test_invalid_key(jwt_auth):
    """Test getting a auth context with invalid signing key."""
    token = create_token(modify=TokenModifier.BAD_KEY)
    expected_error = jwt_auth.AuthContextValidationError
    expected_message = "Not a valid token: Verification failed"
    with raises(expected_error, match=expected_message):
        await jwt_auth.get_context(token)


@mark.asyncio
async def test_invalid_algorithm(jwt_auth):
    """Test getting a auth context with invalid signature algorithm."""
    token = create_token(modify=TokenModifier.BAD_ALG)
    expected_error = jwt_auth.AuthContextValidationError
    expected_message = "Not a valid token: .*Algorithm not allowed"
    with raises(expected_error, match=expected_message):
        await jwt_auth.get_context(token)


@mark.asyncio
async def test_corrupted_token(jwt_auth):
    """Test getting a auth context with corrupted token."""
    token = create_token()
    last_chars = token[-3:]
    last_chars = "bar" if last_chars == "foo" else "foo"
    token = token[:-3] + last_chars
    expected_error = jwt_auth.AuthContextValidationError
    expected_message = "Not a valid token: Verification failed"
    with raises(expected_error, match=expected_message):
        await jwt_auth.get_context(token)


@mark.asyncio
async def test_expired_context(jwt_auth):
    """Test getting an expired auth context."""
    token = create_token(modify=TokenModifier.EXPIRED)
    expected_error = jwt_auth.AuthContextValidationError
    expected_message = "Not a valid token: Expired at"
    with raises(expected_error, match=expected_message):
        await jwt_auth.get_context(token)


@mark.asyncio
async def test_missing_subject(jwt_auth):
    """Test getting a auth context with missing claim."""
    token = create_token(modify=TokenModifier.NO_SUB)
    expected_error = jwt_auth.AuthContextValidationError
    expected_message = "Not a valid token: Claim sub is missing"
    with raises(expected_error, match=expected_message):
        await jwt_auth.get_context(token)


@mark.asyncio
async def test_invalid_subject(jwt_auth):
    """Test getting a auth context with invalid claim."""
    token = create_token(modify=TokenModifier.BAD_SUB)
    expected_error = jwt_auth.AuthContextValidationError
    expected_message = "Not a valid token: Claim .* not a String"
    with raises(expected_error, match=expected_message):
        await jwt_auth.get_context(token)
