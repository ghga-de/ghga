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

"""Unit tests for the core functionality."""

import asyncio

from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest import mark, raises

from top.core.models import LoginInfo, UserInfo
from top.core.oidc_provider import OidcProvider, OidcProviderConfig


def test_create_default_op():
    """Create a default test OP."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)
    assert provider.issuer == "https://op.test"
    assert provider.op_domain == "op.test"
    assert provider.user_domain == "home.org"
    assert provider.client_id == "test-client"
    assert provider.valid_seconds == 60 * 60
    assert not provider.users
    assert provider.serial_id == 1


def test_create_custom_op():
    """Create a custom test OP."""
    config = OidcProviderConfig(
        issuer="https://proxy.aai.lifescience-ri.eu",  # pyright: ignore
        user_domain="dkfz.de",
        client_id="GHGA-Client",
        valid_seconds=90 * 60,
    )
    provider = OidcProvider(config)
    assert provider.issuer == "https://proxy.aai.lifescience-ri.eu"
    assert provider.op_domain == "lifescience-ri.eu"
    assert provider.user_domain == "dkfz.de"
    assert provider.client_id == "GHGA-Client"
    assert provider.valid_seconds == 90 * 60
    assert not provider.users
    assert provider.serial_id == 1


def test_jwks():
    """Test getting the public key set."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)
    jwks = provider.jwks
    assert isinstance(jwks, dict)
    assert list(jwks) == ["keys"]
    keys = jwks["keys"]
    assert isinstance(keys, list)
    assert len(keys) == 1
    key = keys[0]
    assert isinstance(key, dict)
    assert sorted(key) == ["crv", "kid", "kty", "use", "x", "y"]  # no 'd' (public)
    del key["x"]
    del key["y"]
    assert key == {"kty": "EC", "use": "sig", "kid": "test", "crv": "P-256"}


def test_invalid_token():
    """Try to get a user with an invalid token."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)
    with raises(KeyError):
        provider.user_info("bad")


@mark.asyncio
async def test_user_info_for_default_token():
    """Create a default access token for a dummy user."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)

    login = LoginInfo(name="John Doe")  # pyright: ignore
    token = provider.login(login)
    assert isinstance(token, str)
    assert len(provider.users) == 1
    user = provider.user_info(token)
    assert user.name == "John Doe"
    assert user.email == "john.doe@home.org"
    assert user.sub == "id-of-john-doe@op.test"

    assert len(provider.tasks) == 1
    await provider.reset()
    assert not provider.users
    assert not provider.tasks

    with raises(KeyError):
        provider.user_info(token)


@mark.asyncio
async def test_user_info_for_custom_token():
    """Create a custom access token for a dummy user."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)

    login = LoginInfo(
        name="Dr. Jane Roe",
        email="jane@foo.edu",  # pyright: ignore
        sub="sub-of-jane",
        valid_seconds=30,
    )
    token = provider.login(login)
    assert isinstance(token, str)
    assert len(provider.users) == 1
    user = provider.user_info(token)
    assert isinstance(user, UserInfo)
    assert user.name == "Jane Roe"
    assert user.email == "jane@foo.edu"
    assert user.sub == "sub-of-jane"

    assert len(provider.tasks) == 1
    await provider.reset()
    assert not provider.users
    assert not provider.tasks

    with raises(KeyError):
        provider.user_info(token)


@mark.asyncio
async def test_user_info_for_default_token_of_custom_op():
    """Create a custom access token for a dummy user."""
    config = OidcProviderConfig(
        issuer="https://proxy.aai.lifescience-ri.eu",  # pyright: ignore
        user_domain="dkfz.de",
        client_id="GHGA-Client",
        valid_seconds=90 * 60,
    )
    provider = OidcProvider(config)

    login = LoginInfo(name="Frank Foo")  # pyright: ignore
    token = provider.login(login)
    assert isinstance(token, str)
    assert len(provider.users) == 1
    user = provider.user_info(token)
    assert isinstance(user, UserInfo)
    assert user.name == "Frank Foo"
    assert user.email == "frank.foo@dkfz.de"
    assert user.sub == "id-of-frank-foo@lifescience-ri.eu"

    assert len(provider.tasks) == 1
    await provider.reset()
    assert not provider.users
    assert not provider.tasks


@mark.asyncio
async def test_user_infos_for_two_default_tokens():
    """Create two default access tokens for two dummy users."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)

    login = LoginInfo(name="John Doe")  # pyright: ignore
    token1 = provider.login(login)
    login = LoginInfo(name="Dr. Jane Roe")  # pyright: ignore
    token2 = provider.login(login)
    assert token1 != token2
    assert len(provider.users) == 2
    user1 = provider.user_info(token1)
    assert user1.name == "John Doe"
    user2 = provider.user_info(token2)
    assert user2.name == "Jane Roe"
    assert provider.serial_id == 3

    assert len(provider.tasks) == 2
    await provider.reset()
    assert not provider.users
    assert not provider.tasks


@mark.asyncio
async def test_validate_default_tokens():
    """Create two access tokens and validate them."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)

    login = LoginInfo(name="John Doe")  # pyright: ignore
    token = provider.login(login)
    claims = provider.decode_and_validate_token(token)
    assert isinstance(claims, dict)
    keys = " ".join(sorted(claims))
    assert keys == "aud client_id exp iat iss jti scope sid sub token_class"
    assert claims["client_id"] == "test-client"
    assert claims["aud"] == [claims["client_id"]]
    assert claims["iss"] == "https://op.test"
    assert claims["jti"] == "test-1"
    assert claims["sid"] == claims["jti"]
    assert claims["scope"] == "openid profile email"
    assert claims["sub"] == "id-of-john-doe@op.test"
    assert claims["token_class"] == "access_token"
    iat = claims["iat"]
    assert isinstance(iat, int)
    exp = claims["exp"]
    assert isinstance(exp, int)
    assert exp - iat == 60 * 60
    now = now_as_utc().timestamp()
    assert 0 <= now - iat < 5

    login = LoginInfo(
        name="Dr. Jane Roe",
        email="jane@foo.edu",  # pyright: ignore
        sub="sub-of-jane",
        valid_seconds=30,
    )
    token = provider.login(login)
    claims = provider.decode_and_validate_token(token)
    assert isinstance(claims, dict)
    keys = " ".join(sorted(claims))
    assert keys == "aud client_id exp iat iss jti scope sid sub token_class"
    assert claims["client_id"] == "test-client"
    assert claims["aud"] == [claims["client_id"]]
    assert claims["iss"] == "https://op.test"
    assert claims["jti"] == "test-2"
    assert claims["sid"] == claims["jti"]
    assert claims["scope"] == "openid profile email"
    assert claims["sub"] == "sub-of-jane"
    assert claims["token_class"] == "access_token"
    iat = claims["iat"]
    assert isinstance(iat, int)
    exp = claims["exp"]
    assert isinstance(exp, int)
    assert exp - iat == 30
    now = now_as_utc().timestamp()
    assert 0 <= now - iat < 5

    assert len(provider.tasks) == 2
    await provider.reset()
    assert not provider.users
    assert not provider.tasks


@mark.asyncio
async def test_expiration():
    """Check that tokens expire after the specified time."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)

    login = LoginInfo(name="Long John Silver")  # pyright: ignore
    token1 = provider.login(login)

    user1 = provider.user_info(token1)
    assert user1.name == "Long John Silver"

    login = LoginInfo(name="Short John Silver", valid_seconds=0.1)  # pyright: ignore
    token2 = provider.login(login)

    user2 = provider.user_info(token2)
    assert user2.name == "Short John Silver"

    await asyncio.sleep(0.15)

    user1 = provider.user_info(token1)
    assert user1.name == "Long John Silver"

    with raises(KeyError):
        provider.user_info(token2)

    assert len(provider.tasks) == 1
    await provider.reset()
    assert not provider.users
    assert not provider.tasks

    with raises(KeyError):
        provider.user_info(token1)


@mark.asyncio
async def test_more_expiring_tasks():
    """Check that multiple tokens expire after the specified time."""
    config = OidcProviderConfig()  # pyright: ignore
    provider = OidcProvider(config)

    def create_token(name: str, short=False) -> str:
        valid_seconds = 0.1 if short else None
        login = LoginInfo(name=name, valid_seconds=valid_seconds)  # pyright: ignore
        return provider.login(login)

    tokens = [
        (
            create_token(f"Long John Silver {i}"),
            create_token(f"Short John Silver {i}", short=True),
        )
        for i in range(10)
    ]

    await asyncio.sleep(0.15)

    for long_token, short_tokens in tokens:
        assert provider.user_info(long_token).name.startswith("Long")
        with raises(KeyError):
            provider.user_info(short_tokens)

    assert len(provider.tasks) == 10
    await provider.reset()
    assert not provider.users
    assert not provider.tasks

    for long_token, short_tokens in tokens:
        with raises(KeyError):
            assert provider.user_info(long_token)
        with raises(KeyError):
            provider.user_info(short_tokens)
