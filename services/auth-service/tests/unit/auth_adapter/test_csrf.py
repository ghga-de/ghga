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

"""Test the CSRF protection checks."""

from fastapi import HTTPException
from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest import mark, raises

from auth_service.auth_adapter.api.csrf import check_csrf
from auth_service.auth_adapter.core.session_store import Session

NOW = now_as_utc()
EXPECTED_ERROR_MESSAGE = "Invalid or missing CSRF token"

SESSION = Session(
    session_id="some-session-id",
    csrf_token="some-csrf-token",
    user_id="some-user-id",
    user_name="John Doe",
    user_email="john@home.org",
    created=NOW,
    last_used=NOW,
)


@mark.parametrize("method", ["GET", "HEAD", "OPTION"])
def test_check_csrf_on_uncritical_method_without_token(method: str) -> None:
    """Test CSRF protection with an uncritical method and missing token."""
    check_csrf(method, None, SESSION)


@mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_check_csrf_on_critical_method_without_token(method: str) -> None:
    """Test CSRF protection with a critical method and no token."""
    with raises(HTTPException) as exc_info:
        check_csrf(method, None, SESSION)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == EXPECTED_ERROR_MESSAGE


@mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_check_csrf_on_critical_method_with_invalid_token(method: str) -> None:
    """Test CSRF protection with a critical method and and invalid token."""
    with raises(HTTPException) as exc_info:
        check_csrf(method, "another-csrf-token", SESSION)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == EXPECTED_ERROR_MESSAGE


@mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_check_csrf_on_critical_method_with_valid_token(method: str) -> None:
    """Test CSRF protection with a critical method and no token."""
    check_csrf(method, "some-csrf-token", SESSION)


def test_check_csrf_without_session() -> None:
    """Test CSRF protection without session."""
    check_csrf("POST", None, None)
    check_csrf("DELETE", "another-csrf-token", None)
