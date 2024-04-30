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

"""Unit tests for the auth adapter user info retrieval feature"""

import re

from pytest import raises
from pytest_httpx import HTTPXMock

from auth_service.auth_adapter.core import auth

from ...fixtures.utils import create_access_token

USER_INFO = {
    "name": "John Doe",
    "email": "john@home.org",
    "sub": "john@aai.org",
}
RE_USER_INFO_URL = re.compile(".*/userinfo$")


def test_needs_an_access_token():
    """Test that you cannot get user info without an access token."""
    with raises(auth.UserInfoError, match="No access token provided"):
        auth.get_user_info(None)
    with raises(auth.UserInfoError, match="No access token provided"):
        auth.get_user_info("")


def test_rejects_an_expired_access_token():
    """Test that you cannot get user info with an expired token."""
    access_token = create_access_token(expired=True)
    with raises(auth.UserInfoError, match="Not a valid token: Expired"):
        auth.get_user_info(access_token)


def test_rejects_an_access_token_without_sub():
    """Test that you cannot get user info with missing subject."""
    access_token = create_access_token(sub=None)
    with raises(auth.UserInfoError, match="Missing value for sub claim"):
        auth.get_user_info(access_token)


def test_rejects_an_access_token_with_bad_token_class():
    """Test that you cannot get user info with an unexpected token class."""
    access_token = create_access_token(token_class="foo_token")
    with raises(
        auth.UserInfoError,
        match=r"Not a valid token: Invalid 'token_class' value\."
        " Expected 'access_token' got 'foo_token'",
    ):
        auth.get_user_info(access_token)


def test_rejects_user_info_with_mismatch_in_sub(httpx_mock: HTTPXMock):
    """Test that you cannot get user info with a mismatch in subject claims."""
    httpx_mock.add_response(
        url=RE_USER_INFO_URL, json={**USER_INFO, "sub": "not.john@aai.org"}
    )
    access_token = create_access_token()
    with raises(
        auth.UserInfoError,
        match="Subject in userinfo differs from access token",
    ):
        auth.get_user_info(access_token)


def test_rejects_user_info_with_missing_name(httpx_mock: HTTPXMock):
    """Test that you cannot get user info with a missing name in user info."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json={**USER_INFO, "name": None})
    access_token = create_access_token()
    with raises(auth.UserInfoError, match="Missing value for name claim"):
        auth.get_user_info(access_token)


def test_rejects_user_info_with_missing_email(httpx_mock: HTTPXMock):
    """Test that you cannot get user info with missing email in user info."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json={**USER_INFO, "email": None})
    access_token = create_access_token()
    with raises(auth.UserInfoError, match="Missing value for email claim"):
        auth.get_user_info(access_token)


def test_user_info_for_valid_token(httpx_mock: HTTPXMock):
    """Test that you can get user info with a valid token."""
    httpx_mock.add_response(url=RE_USER_INFO_URL, json=USER_INFO)
    access_token = create_access_token()
    user_info = auth.get_user_info(access_token)
    assert user_info is not None
    assert isinstance(user_info, auth.UserInfo)
    assert user_info._asdict() == USER_INFO
