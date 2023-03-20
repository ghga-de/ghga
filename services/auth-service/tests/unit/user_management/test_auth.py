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

"""Test helper functions for handling authentication and authorization."""

from datetime import datetime
from typing import Optional

from fastapi.exceptions import HTTPException
from ghga_service_chassis_lib.utils import UTC, now_as_utc
from jwcrypto import jwk
from pytest import mark, raises

from auth_service.user_management import auth
from auth_service.user_management.user_registry.models.dto import UserStatus

from ...fixtures.utils import create_internal_token, request_with_authorization

# Test the internally used "decode_and_validate_token" function


def test_decodes_and_validates_an_internal_token():
    """Test that a valid internal token is decoded and validated."""

    internal_token = create_internal_token()
    claims = auth.decode_and_validate_token(internal_token)
    assert isinstance(claims, dict)
    assert set(claims) == {
        "name",
        "email",
        "exp",
        "iat",
        "status",
    }
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["status"] == "active"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]


def test_validates_internal_token_with_rsa_signature():
    """Test that an internal tokens with RSA signature can be validated."""
    key = jwk.JWK.generate(kty="RSA", size=1024)
    internal_token = create_internal_token(key=key)
    claims = auth.decode_and_validate_token(internal_token, key=key)
    assert isinstance(claims, dict)
    assert claims["name"] == "John Doe"


def test_validates_internal_token_with_ec_signature():
    """Test that an internal tokens with EC signature can be validated."""
    key = jwk.JWK.generate(kty="EC", crv="P-256")
    internal_token = create_internal_token(key=key)
    claims = auth.decode_and_validate_token(internal_token, key=key)
    assert isinstance(claims, dict)
    assert claims["name"] == "John Doe"


def test_does_not_validate_an_empty_token():
    """Test that an empty internal token rejected."""
    with raises(auth.TokenValidationError, match="Empty token"):
        auth.decode_and_validate_token(None)  # type: ignore
    with raises(auth.TokenValidationError, match="Empty token"):
        auth.decode_and_validate_token("")


def test_does_not_validate_an_internal_token_with_wrong_format():
    """Test that an internal token with a completely wrong format is rejected."""
    internal_token = "random.garbage"
    with raises(auth.TokenValidationError, match="Token format unrecognized"):
        auth.decode_and_validate_token(internal_token)


def test_does_not_validate_an_internal_token_with_bad_signature():
    """Test that an internal token with a corrupt signature is rejected."""
    internal_token = create_internal_token()
    internal_token = ".".join(internal_token.split(".")[:-1] + ["somebadsignature"])
    with raises(
        auth.TokenValidationError,
        match="Not a valid token: Verification failed for all signatures",
    ):
        auth.decode_and_validate_token(internal_token)


def test_does_not_validate_an_internal_token_when_alg_is_not_allowed():
    """Test that an internal token must be signed with an allowed algorithm."""
    internal_token = create_internal_token()
    internal_algs = auth.jwt_config.internal_algs
    assert isinstance(internal_algs, list)
    auth.jwt_config.internal_algs = internal_algs[:]
    try:
        auth.jwt_config.internal_algs.remove("ES256")
        with raises(
            auth.TokenValidationError,
            match="Not a valid token: Verification failed for all signatures",
        ):
            auth.decode_and_validate_token(internal_token)
    finally:
        auth.jwt_config.internal_algs = internal_algs


def test_does_not_validate_an_expired_internal_token():
    """Test that internal tokens that have expired are rejected."""
    internal_token = create_internal_token(expired=True)
    with raises(auth.TokenValidationError, match="Not a valid token: Expired"):
        auth.decode_and_validate_token(internal_token)


def test_does_not_validate_token_with_invalid_payload():
    """Test that internal tokens with invalid payload are rejected."""
    key = jwk.JWK(kty="oct", k="r0TSf_aAU9eS7I5JPPJ20pmkPmR__9LsfnZaKfXZYp8")
    internal_algs = auth.jwt_config.internal_algs
    auth.jwt_config.internal_algs = ["HS256"]
    try:
        token_with_valid_payload = (
            "eyJhbGciOiJIUzI1NiJ9."
            "eyJzdWIiOiAiSm9obiBEb2UifQ."
            "RQYHxFwGjMdVh-umuuA1Yd4Ssx6TAYkg1INYK6_lKVw"
        )
        with raises(
            auth.TokenValidationError, match="Not a valid token: Claim name is missing"
        ):
            auth.decode_and_validate_token(token_with_valid_payload, key=key)
        token_with_text_as_payload = (
            "eyJhbGciOiJIUzI1NiJ9."
            "VGhpcyBpcyBub3QgSlNPTiE."
            "bKt6NQoZGLOLqqqB-XT99ENnsmv-hxLId08FxR4LUOw"
        )
        with raises(
            auth.TokenValidationError, match="Not a valid token: .* not a json dict"
        ):
            auth.decode_and_validate_token(token_with_text_as_payload, key=key)
        token_with_bad_encoding = (
            "eyJhbGciOiJIUzI1NiJ9."
            "eyJzdWIiOiAiRnLpZOlyaWMgQ2hvcGluIn0."
            "8OTfVB6CN2pXgPHZBPdbkqWGd2XhtbVDhlcYdYNh6d4"
        )
        with raises(auth.TokenValidationError, match="'utf-8' codec can't decode"):
            auth.decode_and_validate_token(token_with_bad_encoding, key=key)
    finally:
        auth.jwt_config.internal_algs = internal_algs


# Test the injectable FetchAuthToken  class


@mark.parametrize("fetcher", [auth.FetchAuthToken, auth.RequireAuthToken])
@mark.asyncio
async def test_fetches_internal_token_from_an_authorization_header(fetcher: type):
    """Test that an internal token is fetched from an authorization header."""

    request = request_with_authorization(create_internal_token())

    fetch_auth_token = fetcher()
    token = await fetch_auth_token(request=request)
    assert token
    assert isinstance(token, auth.AuthToken)

    assert token.name == "John Doe"
    assert token.email == "john@home.org"
    assert isinstance(token.iat, datetime)
    assert token.iat.tzinfo is UTC
    assert isinstance(token.exp, datetime)
    assert token.exp.tzinfo is UTC
    assert token.iat <= now_as_utc() < token.exp
    assert token.status == UserStatus.ACTIVE


@mark.parametrize("fetcher", [auth.FetchAuthToken, auth.RequireAuthToken])
@mark.asyncio
async def test_fetches_internal_token_with_additional_attributes(fetcher: type):
    """Test that an internal token with additional attributes can be fetched."""

    request = request_with_authorization(
        create_internal_token(
            id="some-internal-id",
            ext_id="some-id@aai.org",
            role="admin@some.hub",
        )
    )

    fetch_auth_token = fetcher()
    token = await fetch_auth_token(request=request)
    assert token
    assert isinstance(token, auth.AuthToken)

    assert token.name == "John Doe"
    assert token.id == "some-internal-id"
    assert token.ext_id == "some-id@aai.org"
    assert token.status == UserStatus.ACTIVE
    assert token.role == "admin@some.hub"


@mark.parametrize("fetcher", [auth.FetchAuthToken, auth.RequireAuthToken])
@mark.asyncio
async def test_fetches_internal_token_with_unknown_attributes(fetcher: type):
    """Test that unknown attributes in an internal token are silently ignored."""

    request = request_with_authorization(create_internal_token(foo="bar"))

    fetch_auth_token = fetcher()
    token = await fetch_auth_token(request=request)
    assert token
    assert isinstance(token, auth.AuthToken)

    assert token.name == "John Doe"


@mark.parametrize("fetcher", [auth.FetchAuthToken, auth.RequireAuthToken])
@mark.asyncio
async def test_does_not_accept_an_expired_internal_token(fetcher: type):
    """Test that an expired internal token is rejected."""
    request = request_with_authorization(create_internal_token(expired=True))

    fetch_auth_token = fetcher()
    with raises(HTTPException) as exc_info:
        await fetch_auth_token(request=request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not authenticated"


@mark.parametrize("fetcher", [auth.FetchAuthToken, auth.RequireAuthToken])
@mark.parametrize("claim", ["name", "email", "exp", "iat"])
@mark.asyncio
async def test_does_not_accept_an_internal_token_with_missing_claims(
    fetcher: type, claim: str
):
    """Test that an internal token with missing claims is rejected."""
    kwargs = {claim: None}
    token = create_internal_token(**kwargs)  # type: ignore
    request = request_with_authorization(token)

    fetch_auth_token = fetcher()
    with raises(HTTPException) as exc_info:
        await fetch_auth_token(request=request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not authenticated"


@mark.asyncio
async def test_accepts_missing_token_when_optional():
    """Test that internal token is None when not available and fetched as optional."""

    request = request_with_authorization("")
    fetch_auth_token = auth.FetchAuthToken()
    assert await fetch_auth_token(request=request) is None


@mark.asyncio
async def test_does_not_accept_missing_token_when_required():
    """Test that an error is raised when internal token not available and required."""

    request = request_with_authorization("")
    fetch_auth_token = auth.RequireAuthToken()
    with raises(HTTPException) as exc_info:
        assert await fetch_auth_token(request=request) is None

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not authenticated"


@mark.asyncio
async def test_accepts_an_inactive_user_when_optional():
    """Test that no error is raised when an optional user is inactive."""

    request = request_with_authorization(create_internal_token(status="inactive"))

    fetch_auth_token = auth.FetchAuthToken()
    token = await fetch_auth_token(request=request)
    assert token
    assert isinstance(token, auth.AuthToken)

    assert token.name == "John Doe"
    assert token.status == UserStatus.INACTIVE


@mark.asyncio
async def test_does_not_accept_inactive_user_when_required_by_default():
    """Test that an error is raised when the user is inactive and required."""

    request = request_with_authorization(create_internal_token(status="inactive"))
    fetch_auth_token = auth.RequireAuthToken()
    with raises(HTTPException) as exc_info:
        assert await fetch_auth_token(request=request) is None

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not authenticated"


@mark.asyncio
async def test_can_fetch_an_inactive_but_required_user():
    """Test that no error is raised when a required user may be inactive."""

    request = request_with_authorization(create_internal_token(status="inactive"))

    fetch_auth_token = auth.RequireAuthToken(active=False)
    token = await fetch_auth_token(request=request)
    assert token
    assert isinstance(token, auth.AuthToken)

    assert token.name == "John Doe"
    assert token.status == UserStatus.INACTIVE


@mark.parametrize("required_role", [None, "", "admin", "admin@some_hub", "boss"])
@mark.parametrize("user_role", [None, "", "admin", "admin@some.hub", "boss", "user"])
@mark.asyncio
async def test_can_require_a_certain_role(
    required_role: Optional[str], user_role: Optional[str]
):
    """Test that an error is raised when a required role is missing."""

    if not required_role:
        accept = True
    elif "@" in required_role:
        accept = user_role == required_role
    else:
        accept = user_role is not None and user_role.split("@", 1)[0] == required_role

    request = request_with_authorization(create_internal_token(role=user_role))

    fetch_auth_token = auth.RequireAuthToken(role=required_role)

    if accept:
        token = await fetch_auth_token(request=request)
        assert token
        assert isinstance(token, auth.AuthToken)

        assert token.name == "John Doe"
        assert token.role == user_role

    else:
        with raises(HTTPException) as exc_info:
            await fetch_auth_token(request=request)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Not authenticated"
