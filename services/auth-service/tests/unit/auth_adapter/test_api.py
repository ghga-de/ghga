# Copyright 2021 - 2023 Universität Tübingen, DKFZ and EMBL
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

"""Unit tests for the auth adapter API"""

from auth_service.auth_adapter.api.headers import get_bearer_token


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
