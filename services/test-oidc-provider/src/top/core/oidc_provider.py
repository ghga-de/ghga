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

"""Test OpenID Connect provider"""

import asyncio
import string
from contextlib import suppress
from secrets import choice
from typing import Any
from urllib.parse import urlencode

from ghga_service_commons.utils.jwt_helpers import (
    decode_and_validate_token,
    generate_jwk,
    sign_and_serialize_token,
)
from jwcrypto import jwk
from pydantic import AnyHttpUrl, Field, PositiveInt
from pydantic_settings import BaseSettings
from typing_extensions import TypedDict

from .models import LoginInfo, TokenResponse, UserInfo

__all__ = ["Jwks", "OidcProvider", "OidcProviderConfig"]


type Code2Token = dict[str, str]  # maps authorization codes to access tokens
type Token2User = dict[str, UserInfo]  # maps access tokens to user info

CODE_CHARS = string.ascii_letters + string.digits  # alphabet for authorization codes
CODE_LEN = 32  # length of the authorization code
SCOPE = "openid profile email"  # default scope for the authorization code flow


class Jwks(TypedDict):
    """A JSON Web Key Set as a dictionary."""

    keys: list[dict[str, str]]


class OidcProviderConfig(BaseSettings):
    """The configuration for a test OpenID Connect provider."""

    issuer: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://op.test"), description="test issuer URL"
    )
    user_domain: str = Field(
        default="home.org",
        description="domain name of the home organization of the test users",
    )
    client_id: str = Field(default="test-client", description="test client ID")
    redirect_url: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://client.test/oauth/callback"),
        description="test redirect URL",
    )
    valid_seconds: PositiveInt = Field(
        default=60 * 60,
        description="default expiration time of access tokens in seconds",
    )


class OidcProvider:
    """A test OpenID Connect provider."""

    tokens: Code2Token
    users: Token2User
    key_set: jwk.JWKSet
    issuer: str
    op_domain: str
    user_domain: str
    client_id: str
    serial_id: int
    tasks: set[asyncio.Task]

    def __init__(self, config: OidcProviderConfig) -> None:
        """Initialize the OP."""
        issuer = str(config.issuer).rstrip("/")
        self.issuer = issuer
        if not issuer or "://" not in issuer or "." not in issuer:
            raise ValueError(f"Invalid issuer: {issuer!r}")
        user_domain = config.user_domain
        if not user_domain or "://" in user_domain or "." not in user_domain:
            raise ValueError(f"Invalid user domain: {user_domain!r}")
        self.op_domain = ".".join(
            issuer.split("://", 1)[-1].split("/", 1)[0].rsplit(".", 2)[-2:]
        )
        self.valid_seconds = config.valid_seconds
        self.user_domain = str(user_domain)
        self.client_id = config.client_id
        self.redirect_url = str(config.redirect_url)
        self._generate_keys()
        self.tokens = {}
        self.users = {}
        self.serial_id = 1
        self.tasks = set()

    async def _cancel_tasks(self):
        """Cleanup all pending tasks."""
        tasks = self.tasks
        while tasks:
            task = tasks.pop()
            if not task.done():
                try:
                    task.cancel()
                    await task
                except (RuntimeError, asyncio.CancelledError):
                    pass

    async def reset(self):
        """Reset the OP, clear all data."""
        await self._cancel_tasks()
        self.tokens.clear()
        self.users.clear()
        self.serial_id = 1

    def _add_user(self, token: str, user: UserInfo) -> None:
        """Add the given user to the cache."""
        self.users[token] = user
        self.serial_id += 1

    def _generate_keys(self) -> None:
        """Generate a key set with a key pair for signing the tokens."""
        key = generate_jwk()  # generates EC keys
        key.update(kid="test", use="sig")
        key_set = jwk.JWKSet()
        key_set.add(key)
        self.key_set = key_set

    @property
    def key(self) -> jwk.JWK:
        """Get the single key pair from the key set."""
        key = self.key_set.get_key("test")
        if key is None:
            raise KeyError("Cannot retrieve the signing key.")
        return key

    @property
    def jwks(self) -> Jwks:
        """Get the public key set."""
        return self.key_set.export(private_keys=False, as_dict=True)

    def _add_cleanup_task(self, token: str, valid_seconds: int | float) -> None:
        """Add a task to remove the token in the cache after the given time."""

        async def cleanup_task(token: str, valid_seconds: int | float) -> None:
            """Remove the given token in the cache after the given time."""
            await asyncio.sleep(valid_seconds)
            if token in self.users:
                del self.users[token]
            self.tasks.remove(task)

        task = asyncio.create_task(cleanup_task(token, valid_seconds))
        self.tasks.add(task)

    def login(self, login_info: LoginInfo) -> str:
        """Login as a user and cache an access token for authorization.

        If no subject identifier is passed, it is derived from the user name.

        Returns an access token that can be used to fetch the user info.
        """
        name = login_info.name.strip()
        valid_seconds = login_info.valid_seconds
        if valid_seconds is None:
            valid_seconds = self.valid_seconds
        if name.startswith(("Dr.", "Prof.")):
            name = name.split(".", 1)[-1].lstrip()
        if login_info.email is None:
            user_name = name.lower().replace(" ", ".")
            email = f"{user_name}@{self.user_domain}"
        else:
            email = str(login_info.email)
        sub = login_info.sub
        if not sub:
            user_name = name.lower().replace(" ", "-")
            user_id = f"id-of-{user_name}"
            sub = f"{user_id}@{self.op_domain}"
        user = UserInfo(sub=sub, email=email, name=name)
        jti = f"test-{self.serial_id}"
        claims = {
            "aud": [self.client_id],
            "sub": sub,
            "scope": SCOPE,
            "iss": self.issuer,
            "client_id": self.client_id,
            "jti": jti,
        }
        token = sign_and_serialize_token(
            claims,
            key=self.key,
            valid_seconds=int(valid_seconds),
        )
        self._add_user(token, user)
        self._add_cleanup_task(token, valid_seconds)
        return token

    @staticmethod
    def _create_code() -> str:
        """Create a random code for the authorization code flow."""
        return "".join(choice(CODE_CHARS) for _ in range(CODE_LEN))

    def authorize(
        self,
        response_type: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        state: str,
    ) -> str:
        """Generate a callback URL with authorization code.

        The code will authorize the client as the last logged in user.
        """
        error = msg = token = None
        if redirect_uri != self.redirect_url:
            msg = f"Invalid redirect URI: {redirect_uri!r}, expected {self.redirect_url!r}"
            raise ValueError(msg)
        if response_type != "code":
            error = "invalid_response_type"
            msg = f"Invalid response type: {response_type!r}, expected 'code'"
        elif "openid" not in scope.split():
            error = "invalid_scope"
            msg = f"Invalid scope: {scope!r}, expected 'openid'"
        elif not state:
            error = "missing_state"
            msg = "Missing state"
        elif client_id != self.client_id:
            error = "unauthorized_client"
            msg = f"Invalid client ID: {client_id!r}, expected {self.client_id!r}"
        else:
            with suppress(StopIteration):
                token = next(reversed(self.users))
            if not token:
                error = "login_required"
                msg = "User did not log in"
        if error or not token:
            params = {"error": error, "error_description": msg}
        else:
            code = self._create_code()
            self.tokens[code] = token
            params = {"code": code}
        params["state"] = state
        return f"{redirect_uri}?{urlencode(params)}"

    def token(
        self,
        grant_type: str,
        code: str,
        redirect_uri: str,
        client_id: str,
    ) -> TokenResponse:
        """Exchange an authorization code for an access token.

        This does not return an ID token on purpose,
        so that the client needs to request the user info separately.
        """
        msg = None
        if grant_type != "authorization_code":
            msg = f"Invalid grant type: {grant_type!r}, expected 'authorization_code'"
        elif client_id != self.client_id:
            msg = f"Invalid client ID: {client_id!r}, expected {self.client_id!r}"
        elif redirect_uri != self.redirect_url:
            msg = f"Invalid redirect URI: {redirect_uri!r}, expected {self.redirect_url!r}"
        if code not in self.tokens:
            msg = "Authorization code is invalid or expired"
        if msg:
            raise ValueError(msg)
        access_token = self.tokens.pop(code)
        return TokenResponse(
            access_token=access_token,
            expires_in=int(self.valid_seconds),
            scope=SCOPE,
        )

    def user_info(self, token: str) -> UserInfo:
        """Return the user info associated with the given access token.

        Raises a KeyError if no user info is associated with the given token.
        This means the token is invalid in the context of this OP provider.
        """
        return self.users[token]

    def decode_and_validate_token(self, token: str) -> dict[str, Any]:
        """Decode and validate the given token."""
        return decode_and_validate_token(token, self.key)
