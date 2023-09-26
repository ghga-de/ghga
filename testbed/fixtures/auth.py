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

"""Fixture for testing APIs that use the internal auth token."""

from pathlib import Path
from typing import Optional

import httpx
from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token
from jwcrypto import jwk
from pytest import fixture

from .config import Config

__all__ = ["auth_fixture"]

DEFAULT_VALID_SECONDS = 60 * 60  # 10 mins
DEFAULT_USER_STATUS = "active"
TIMEOUT = 10


class TokenGenerator:
    """Generator for internal auth tokens"""

    key_file: Path
    use_auth_adapter: bool
    auth_adapter_url: str
    op_url: str
    op_issuer: str
    titles = ("Dr.", "Prof.")
    user_domain = "home.org"

    def __init__(self, config: Config):
        self.use_auth_adapter = config.use_auth_adapter
        self.key_file = config.auth_key_file
        self.op_url = config.op_url
        self.op_issuer = config.op_issuer
        self.auth_adapter_url = config.auth_adapter_url

    @classmethod
    def split_title(cls, full_name: str) -> tuple[Optional[str], str]:
        """Split the full name into title and actual name."""
        if full_name.startswith(cls.titles):
            title, name = full_name.split(None, 1)
        else:
            title, name = None, full_name
        return title, name

    def get_user_id(self, full_name: str) -> str:
        """Get the plain identifier of the user without the domain."""
        name = self.split_title(full_name)[1]
        return "id-of-" + name.lower().replace(" ", "-")

    def get_sub(self, full_name: str) -> str:
        """Get the subject identifier of the user with the given full name."""
        user_id = self.get_user_id(full_name)
        op_domain = ".".join(
            self.op_issuer.split("://", 1)[-1].split("/", 1)[0].rsplit(".", 2)[-2:]
        )
        return f"{user_id}@{op_domain}"

    def get_email(self, full_name: str) -> str:
        """Get the email address of the user with the given full name."""
        name = self.split_title(full_name)[1]
        mail_id = name.lower().replace(" ", ".")
        return f"{mail_id}@{self.user_domain}"

    def external_access_token_from_name(
        self,
        name: str,
        email: Optional[str] = None,
        sub: Optional[str] = None,
        valid_seconds: Optional[int] = None,
    ):
        """Create an external access token for the given name and email address."""
        if not valid_seconds:
            valid_seconds = DEFAULT_VALID_SECONDS
        login_info = {
            "name": name,
            "email": email,
            "valid_seconds": DEFAULT_VALID_SECONDS,
        }
        if sub:
            login_info["sub"] = sub
        url = self.op_url + "/login"
        response = httpx.post(url, json=login_info, timeout=TIMEOUT)
        assert response.status_code == 201
        token = response.text
        assert token and token.count(".") == 2
        return token

    def internal_access_token_from_external_access_token(
        self, token: str, for_registration: bool = False
    ) -> str:
        """Get an internal from an external access token using the auth adapter."""
        url = self.auth_adapter_url + "/users"
        method = httpx.post if for_registration else httpx.get
        headers = {"Authorization": f"Bearer {token}"}
        response = method(url, headers=headers, timeout=TIMEOUT)  # type: ignore
        assert response.status_code == 200
        assert not response.json()
        authorization = response.headers.get("Authorization")
        assert authorization and authorization.startswith("Bearer ")
        token = authorization.split(None, 1)[-1]
        assert token and token.count(".") == 2
        return token

    def internal_access_token_from_name(
        self,
        name: str,
        email: Optional[str] = None,
        title: Optional[str] = None,
        sub: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        valid_seconds: Optional[int] = None,
    ) -> str:
        """Create an internal access token for the given name and email address."""
        email = self.get_email(name)
        role = "data_steward" if "steward" in name.lower() else None
        if not status:
            status = DEFAULT_USER_STATUS
        claims = {
            "name": name,
            "email": email,
            "title": title,
            "role": role,
            "status": status,
        }
        if user_id:
            claims["id"] = user_id
        if sub:
            claims["ext_id"] = sub
        if not valid_seconds:
            valid_seconds = DEFAULT_VALID_SECONDS
        return sign_and_serialize_token(claims, self.key, valid_seconds)

    def generate_headers(
        self,
        name: str,
        email: Optional[str] = None,
        title: Optional[str] = None,
        user_id: Optional[str] = None,
        valid_seconds: int = DEFAULT_VALID_SECONDS,
    ) -> dict[str, str]:
        """Generate headers with internal auth token with specified claims."""
        if title is None:
            title, name = self.split_title(name)
        sub = None if user_id else self.get_sub(name)
        if self.use_auth_adapter:
            token = self.external_access_token_from_name(
                name=name, email=email, sub=sub, valid_seconds=valid_seconds
            )
            token = self.internal_access_token_from_external_access_token(
                token, for_registration=not user_id
            )
        else:
            token = self.internal_access_token_from_name(
                name=name,
                email=email,
                title=title,
                sub=sub,
                user_id=user_id,
                valid_seconds=valid_seconds,
            )
        return {"Authorization": f"Bearer {token}"}

    @property
    def key(self) -> jwk.JWK:
        """Read the signing key from a local env file."""
        with open(self.key_file, encoding="ascii") as key_file:
            for line in key_file:
                if line.startswith("AUTH_SERVICE_AUTH_KEY="):
                    return jwk.JWK.from_json(line.split("=", 1)[1].rstrip().strip("'"))
        raise RuntimeError("Cannot read signing key for authentication")

    @property
    def simple_token(self) -> str:
        """Read the simple token from a local env file."""
        with open(self.key_file, encoding="ascii") as key_file:
            for line in key_file:
                if line.startswith("SIMPLE_TOKEN="):
                    return line.split("=", 1)[1].rstrip().strip('"')
        raise RuntimeError("Cannot read simple token for authentication")


@fixture(name="auth", scope="session")
def auth_fixture(config) -> TokenGenerator:
    """Fixture that provides an internal auth token generator."""

    return TokenGenerator(config)
