# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Unit tests for the auth adapter HTTP Basic authentication feature"""

import pytest
from fastapi.security import HTTPBasicCredentials

from auth_service.auth_adapter.rest.basic import get_allowed_credentials
from auth_service.config import Config


def test_default_no_allowed_credentials():
    """Test that by default, no Basic auth credentials are set"""
    config = Config()  # type: ignore
    assert not get_allowed_credentials(config)


def test_set_credentials():
    """Test that three user names and passwords can be set."""
    config = Config(basic_auth_credentials="foo:oof bar:rab baz:zab")  # type: ignore
    assert get_allowed_credentials(config) == [
        HTTPBasicCredentials(username="foo", password="oof"),
        HTTPBasicCredentials(username="bar", password="rab"),
        HTTPBasicCredentials(username="baz", password="zab"),
    ]


def test_invalid_credentials():
    """Test that invalid credentials are detected."""
    config = Config(basic_auth_credentials="foo:oof rhubarb baz:zab")  # type: ignore
    with pytest.raises(ValueError, match="must be passed as username:password"):
        get_allowed_credentials(config)


def test_password_contains_a_colon():
    """Test that passwords with a colon are treated properly."""
    config = Config(basic_auth_credentials="foo:bar:baz")  # type: ignore
    assert get_allowed_credentials(config) == [
        HTTPBasicCredentials(username="foo", password="bar:baz"),
    ]
