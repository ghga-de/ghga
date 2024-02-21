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

"""Unit tests for the request and response header utilities."""

from ghga_service_commons.utils.utc_dates import now_as_utc

from auth_service.auth_adapter.api.headers import get_bearer_token, session_to_header
from auth_service.auth_adapter.core.session_store import Session

NOW = now_as_utc()


def test_get_bearer_token_no_headers():
    """Test that None is returned when there are no headers."""
    assert get_bearer_token() is None
    assert get_bearer_token(None) is None
    assert get_bearer_token(None, None) is None


def test_get_bearer_token_invalid_headers():
    """Test that None is returned when there are no bearer tokens."""
    assert get_bearer_token("Basic token") is None
    assert get_bearer_token("Still not a Bearer token") is None
    assert get_bearer_token("foo", "bar") is None
    assert get_bearer_token("Basic token", "Invalid token", "Basic token") is None


def test_get_bearer_token_one_header():
    """Test that bearer token is returned when there is one header."""
    assert get_bearer_token("Bearer foo-bar") == "foo-bar"


def test_get_bearer_token_multiple_header():
    """Test that first bearer token is returned when there are multiple headers."""
    assert get_bearer_token("Bearer foo-bar", "Bearer bar-foo") == "foo-bar"
    assert get_bearer_token(None, "Bearer foo-bar") == "foo-bar"
    assert get_bearer_token("Bearer foo-bar", None) == "foo-bar"
    assert get_bearer_token("Bearer foo-bar", "Basic foo:bar") == "foo-bar"
    assert get_bearer_token("Basic foo:bar", "Bearer foo-bar") == "foo-bar"


def test_session_to_header_ascii():
    """Test that a session with ascii values is properly converted to a header."""
    session = Session(
        session_id="some-session-id",
        user_id="some-user-id",
        user_name="John Doe",
        user_email="john@home.org",
        csrf_token="some-csrf-token",
        created=NOW,
        last_used=NOW,
    )
    assert session_to_header(session) == (
        '{"userId":"some-user-id","name":"John Doe","email":"john@home.org",'
        '"state":"NeedsRegistration","csrf":"some-csrf-token"}'
    )


def test_session_to_header_non_ascii():
    """Test that a session with non-ascii values is properly converted to a header."""
    session = Session(
        session_id="a-session-id",
        user_id="a-user-id",
        user_name="Svante Pääbo",
        user_email="svante@home.se",
        csrf_token="a-csrf-token",
        created=NOW,
        last_used=NOW,
    )
    assert session_to_header(session) == (
        '{"userId":"a-user-id","name":"Svante Pääbo","email":"svante@home.se",'
        '"state":"NeedsRegistration","csrf":"a-csrf-token"}'
    )


def test_session_to_header_with_optional_properties():
    """Test that the optional properties of a session can also be converted."""
    session = Session(
        session_id="some-session-id",
        user_id="some-user-id",
        user_name="John Doe",
        user_email="john@home.org",
        user_title="Dr.",
        csrf_token="some-csrf-token",
        created=NOW,
        last_used=NOW,
    )
    assert session_to_header(session, lambda _session: (42, 144)) == (
        '{"userId":"some-user-id","name":"John Doe","email":"john@home.org",'
        '"state":"NeedsRegistration","csrf":"some-csrf-token",'
        '"title":"Dr.","timeout":42,"extends":144}'
    )
