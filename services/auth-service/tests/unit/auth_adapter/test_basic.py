# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Unit tests for the Basic Auth feature"""

from fastapi.security import HTTPBasicCredentials
from pytest import raises

from auth_service.auth_adapter.api.basic import get_allowed_credentials
from auth_service.config import Config


def test_default_no_allowed_credentials():
    """Test that by default, no Basic auth credentials are set"""
    assert get_allowed_credentials(Config()) == []


def test_single_credentials_separately():
    """Test that a single user name and password can be set separately."""
    assert get_allowed_credentials(
        Config(basic_auth_user="foo", basic_auth_pwd="bar")
    ) == [HTTPBasicCredentials(username="foo", password="bar")]


def test_single_credentials_combined():
    """Test that a single user name and password can be set combined."""
    assert get_allowed_credentials(Config(basic_auth_user="foo:bar")) == [
        HTTPBasicCredentials(username="foo", password="bar")
    ]


def test_three_credentials_separately():
    """Test that three user names and passwords can be set separately."""
    assert get_allowed_credentials(
        Config(basic_auth_user="foo,bar,baz", basic_auth_pwd="oof,rab,zab")
    ) == [
        HTTPBasicCredentials(username="foo", password="oof"),
        HTTPBasicCredentials(username="bar", password="rab"),
        HTTPBasicCredentials(username="baz", password="zab"),
    ]


def test_three_credentials_combined():
    """Test that three user names and passwords can be set combined."""
    assert get_allowed_credentials(
        Config(basic_auth_user="foo:oof,bar:rab,baz:zab")
    ) == [
        HTTPBasicCredentials(username="foo", password="oof"),
        HTTPBasicCredentials(username="bar", password="rab"),
        HTTPBasicCredentials(username="baz", password="zab"),
    ]


def test_user_without_password():
    """Test that two separate users with three passwords raise a ValueError."""
    with raises(ValueError):
        assert get_allowed_credentials(Config(basic_auth_user="foo"))
    with raises(ValueError):
        assert get_allowed_credentials(Config(basic_auth_user="foo:"))
    with raises(ValueError):
        assert get_allowed_credentials(Config(basic_auth_user="foo", basic_auth_pwd=""))


def test_password_without_user():
    """Test that two separate users with three passwords raise a ValueError."""
    with raises(ValueError):
        assert get_allowed_credentials(Config(basic_auth_pwd="foo"))
    with raises(ValueError):
        assert get_allowed_credentials(Config(basic_auth_user=":foo"))
    with raises(ValueError):
        assert get_allowed_credentials(Config(basic_auth_user="", basic_auth_pwd="foo"))


def test_two_users_but_three_passwords_separately():
    """Test that two separate users with three passwords raise a ValueError."""
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="foo,bar", basic_auth_pwd="oof,rab,zab")
        )
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="foo,bar,", basic_auth_pwd="oof,rab,zab")
        )
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="foo,,baz", basic_auth_pwd="oof,rab,zab")
        )


def test_three_users_but_two_passwords_separately():
    """Test that three separate users with two passwords raise a ValueError."""
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="foo,bar,baz", basic_auth_pwd="oof,rab")
        )
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="foo,bar,baz", basic_auth_pwd="oof,rab,")
        )
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="foo,bar,baz", basic_auth_pwd="oof,,zab")
        )


def test_whitespace_is_trimmed():
    """Test that whitespace around usernames and passwords is ignored."""
    assert get_allowed_credentials(
        Config(basic_auth_user="  foo  ", basic_auth_pwd="  bar  ")
    ) == [HTTPBasicCredentials(username="foo", password="bar")]
    assert get_allowed_credentials(Config(basic_auth_user="  foo  :  bar  ")) == [
        HTTPBasicCredentials(username="foo", password="bar")
    ]
    assert get_allowed_credentials(
        Config(
            basic_auth_user="  foo  ,  bar  ,  baz  ",
            basic_auth_pwd="  oof  ,  rab  ,  zab ",
        )
    ) == [
        HTTPBasicCredentials(username="foo", password="oof"),
        HTTPBasicCredentials(username="bar", password="rab"),
        HTTPBasicCredentials(username="baz", password="zab"),
    ]
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="  ", basic_auth_pwd="foo")
        )
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="foo", basic_auth_pwd="  ")
        )
    with raises(ValueError):
        assert get_allowed_credentials(
            Config(basic_auth_user="foo,bar,baz", basic_auth_pwd="oof,  ,zab")
        )
