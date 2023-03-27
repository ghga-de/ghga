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

"""Unit tests for the auth adapter core token exchange feature"""

import re

from ghga_service_chassis_lib.utils import now_as_utc
from pydantic import EmailStr
from pytest import mark, raises

from auth_service.auth_adapter.core import auth
from auth_service.user_management.user_registry.models.dto import (
    AcademicTitle,
    UserStatus,
)

from ...fixtures.utils import (
    DummyClaimDao,
    DummyUserDao,
    create_access_token,
    get_claims_from_token,
)

USER_INFO = {
    "name": "John Doe",
    "email": "john@home.org",
    "sub": "john@aai.org",
}
RE_USER_INFO_URL = re.compile(".*/userinfo$")


@mark.asyncio
async def test_rejects_an_expired_access_token():
    """Test the token exchange for a user with an expired token."""
    access_token = create_access_token(expired=True)
    with raises(auth.TokenValidationError, match="Not a valid token: Expired"):
        await auth.exchange_token(access_token)


@mark.asyncio
async def test_rejects_an_access_token_without_sub():
    """Test the token exchange for a token with missing subject."""
    access_token = create_access_token(sub=None)
    with raises(auth.TokenValidationError, match="Missing value for sub claim"):
        await auth.exchange_token(access_token)


@mark.asyncio
async def test_rejects_an_access_token_with_bad_token_class():
    """Test the token exchange for a token with an unexpected token class."""
    access_token = create_access_token(token_class="foo_token")
    with raises(
        auth.TokenValidationError,
        match=r"Not a valid token: Invalid 'token_class' value\."
        " Expected 'access_token' got 'foo_token'",
    ):
        await auth.exchange_token(access_token)


@mark.asyncio
async def test_rejects_user_info_with_mismatch_in_sub(httpx_mock):
    """Test the token exchange for a mismatch in subject claims."""
    access_token = create_access_token()
    user_dao = DummyUserDao(ext_id=EmailStr("not.john@aai.org"))
    httpx_mock.add_response(
        url=RE_USER_INFO_URL, json={**USER_INFO, "sub": "john@foo.org"}
    )
    with raises(
        auth.UserInfoError,
        match="Subject in userinfo differs from access token",
    ):
        await auth.exchange_token(access_token, pass_sub=True, user_dao=user_dao)


@mark.asyncio
async def test_rejects_user_info_with_missing_name(httpx_mock):
    """Test the token exchange for a missing name in user info."""
    access_token = create_access_token()
    user_dao = DummyUserDao(ext_id=EmailStr("not.john@aai.org"))
    user_info = {**USER_INFO, "name": None}  # type: ignore
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=user_info)
    with raises(auth.UserInfoError, match="Missing value for name claim"):
        await auth.exchange_token(access_token, pass_sub=True, user_dao=user_dao)


@mark.asyncio
async def test_rejects_user_info_with_missing_email(httpx_mock):
    """Test the token exchange for a missing email in user info."""
    access_token = create_access_token()
    user_dao = DummyUserDao(ext_id=EmailStr("not.john@aai.org"))
    user_info = {**USER_INFO, "email": None}  # type: ignore
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=user_info)
    with raises(auth.UserInfoError, match="Missing value for email claim"):
        await auth.exchange_token(access_token, pass_sub=True, user_dao=user_dao)


@mark.asyncio
async def test_exchanges_token_for_unknown_user_if_requested(httpx_mock):
    """Test token exchange for a valid but unknown user with pass_sub flag."""
    access_token = create_access_token()
    user_dao = DummyUserDao(ext_id="not.john@aai.org")
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)
    internal_token = await auth.exchange_token(
        access_token, pass_sub=True, user_dao=user_dao
    )
    assert internal_token is not None
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"email", "name", "ext_id", "exp", "iat"}
    assert set(claims) == expected_claims
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["ext_id"] == "john@aai.org"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]


@mark.asyncio
async def test_does_not_exchange_for_unknown_user_if_not_requested():
    """Test token exchange for a valid but unknown user without pass_sub flag."""
    access_token = create_access_token()
    user_dao = DummyUserDao(ext_id=EmailStr("not.john@aai.org"))
    assert await auth.exchange_token(access_token, user_dao=user_dao) is None


@mark.asyncio
async def test_exchanges_access_token_for_a_known_user(httpx_mock):
    """Test the token exchange for a valid and already known user."""
    access_token = create_access_token()
    user_dao, claim_dao = DummyUserDao(), DummyClaimDao()
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)
    internal_token = await auth.exchange_token(
        access_token, user_dao=user_dao, claim_dao=claim_dao
    )
    assert internal_token is not None
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"email", "name", "id", "status", "title", "exp", "iat"}
    assert set(claims) == expected_claims
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["id"] == "john@ghga.de"
    assert claims["status"] == "active"
    assert claims["title"] is None
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]
    assert user_dao.user.status is UserStatus.ACTIVE
    assert user_dao.user.status_change is None


@mark.asyncio
async def test_also_passes_sub_for_a_known_user(httpx_mock):
    """Test that the sub claim is also passed for an already known user."""
    access_token = create_access_token()
    user_dao, claim_dao = DummyUserDao(), DummyClaimDao()
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)
    internal_token = await auth.exchange_token(
        access_token, pass_sub=True, user_dao=user_dao, claim_dao=claim_dao
    )
    assert internal_token is not None
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    assert claims["id"] == "john@ghga.de"
    assert claims["ext_id"] == "john@aai.org"


@mark.asyncio
async def test_exchanges_access_token_when_name_was_changed(httpx_mock):
    """Test the token exchange for a valid user with a different name."""
    access_token = create_access_token()
    user_dao = DummyUserDao(name="John Foo")
    httpx_mock.add_response(url=re.compile(".*/userinfo$"), json=USER_INFO)
    internal_token = await auth.exchange_token(access_token, user_dao=user_dao)
    assert internal_token is not None
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"email", "name", "id", "status", "title", "exp", "iat"}
    assert set(claims) == expected_claims
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["id"] == "john@ghga.de"
    assert claims["status"] == "invalid"
    assert claims["title"] is None
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]
    user = user_dao.user
    assert user.status is UserStatus.ACTIVE
    assert user.status_change is None


@mark.asyncio
async def test_exchanges_access_token_when_email_was_changed(httpx_mock):
    """Test the token exchange for a valid user with a different email."""
    access_token = create_access_token()
    user_dao = DummyUserDao(email=EmailStr("john@elsewhere.org"))
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)
    internal_token = await auth.exchange_token(access_token, user_dao=user_dao)
    assert internal_token is not None
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"email", "name", "id", "status", "title", "exp", "iat"}
    assert set(claims) == expected_claims
    assert claims["name"] == "John Doe"
    assert claims["email"] == "john@home.org"
    assert claims["id"] == "john@ghga.de"
    assert claims["status"] == "invalid"
    assert claims["title"] is None
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    assert claims["iat"] <= int(now_as_utc().timestamp()) < claims["exp"]
    user = user_dao.user
    assert user.status is UserStatus.ACTIVE
    assert user.status_change is None


@mark.asyncio
async def test_adds_role_for_a_known_data_steward(httpx_mock):
    """Test that the internal token contains the role for a data steward."""
    access_token = create_access_token()
    user_dao, claim_dao = (
        DummyUserDao(id_="james@ghga.de", title=AcademicTitle.DR),
        DummyClaimDao(),
    )
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)
    internal_token = await auth.exchange_token(
        access_token, user_dao=user_dao, claim_dao=claim_dao
    )
    assert internal_token is not None
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"email", "name", "id", "status", "title", "exp", "iat", "role"}
    assert set(claims) == expected_claims
    assert claims["id"] == "james@ghga.de"
    assert claims["status"] == "active"
    assert claims["title"] == "Dr."

    assert claims["role"] == "data_steward"


@mark.asyncio
async def test_does_not_add_role_for_a_known_inactive_data_steward(httpx_mock):
    """Test that the token does not contain the role for an inactive data steward."""
    access_token = create_access_token()
    user_dao, claim_dao = (
        DummyUserDao(
            id_="james@ghga.de", title=AcademicTitle.DR, status=UserStatus.INACTIVE
        ),
        DummyClaimDao(),
    )
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)
    internal_token = await auth.exchange_token(
        access_token, user_dao=user_dao, claim_dao=claim_dao
    )
    assert internal_token is not None
    claims = get_claims_from_token(internal_token)
    assert isinstance(claims, dict)
    expected_claims = {"email", "name", "id", "status", "title", "exp", "iat"}
    assert set(claims) == expected_claims
    assert claims["id"] == "james@ghga.de"
    assert claims["status"] == "inactive"
    assert claims["title"] == "Dr."
