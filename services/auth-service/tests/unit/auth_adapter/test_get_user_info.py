# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

import pytest

from auth_service.auth_adapter.core import auth
from ghga_service_commons.api.mock_router import MockRouter

from ...fixtures.utils import create_access_token, mock_userinfo

USER_INFO = {
    "name": "John Doe",
    "email": "john@home.org",
    "sub": "john@aai.org",
}


def test_needs_an_access_token():
    """Test that you cannot get user info without an access token."""
    with pytest.raises(auth.UserInfoError, match="No access token provided"):
        auth.get_user_info(None)
    with pytest.raises(auth.UserInfoError, match="No access token provided"):
        auth.get_user_info("")


def test_rejects_an_expired_access_token():
    """Test that you cannot get user info with an expired token."""
    access_token = create_access_token(expired=True)
    with pytest.raises(auth.UserInfoError, match="Not a valid token: Expired"):
        auth.get_user_info(access_token)


@pytest.mark.parametrize("claim", ["sub", "aud", "scope"])
def test_rejects_an_access_token_without_mandatory_claim(claim: str):
    """Test that you cannot get user info with missing claims."""
    access_token = create_access_token(**{claim: None})  # type: ignore
    with pytest.raises(auth.UserInfoError, match=f"Missing value for {claim} claim"):
        auth.get_user_info(access_token)


def test_rejects_user_info_with_mismatch_in_sub(mock_router: MockRouter):
    """Test that you cannot get user info with a mismatch in subject claims."""
    mock_userinfo(mock_router, {**USER_INFO, "sub": "not.john@aai.org"})
    access_token = create_access_token()
    with pytest.raises(
        auth.UserInfoError,
        match="Subject in userinfo differs from access token",
    ):
        auth.get_user_info(access_token)


def test_rejects_user_info_with_missing_name(mock_router: MockRouter):
    """Test that you cannot get user info with a missing name in user info."""
    mock_userinfo(mock_router, {**USER_INFO, "name": None})
    access_token = create_access_token()
    with pytest.raises(auth.UserInfoError, match="Missing value for name claim"):
        auth.get_user_info(access_token)


def test_rejects_user_info_with_missing_email(mock_router: MockRouter):
    """Test that you cannot get user info with missing email in user info."""
    mock_userinfo(mock_router, {**USER_INFO, "email": None})
    access_token = create_access_token()
    with pytest.raises(auth.UserInfoError, match="Missing value for email claim"):
        auth.get_user_info(access_token)


def test_user_info_for_valid_token(mock_router: MockRouter):
    """Test that you can get user info with a valid token."""
    mock_userinfo(mock_router, USER_INFO)
    access_token = create_access_token()
    user_info = auth.get_user_info(access_token)
    assert user_info is not None
    assert isinstance(user_info, auth.UserInfo)
    assert user_info._asdict() == USER_INFO
