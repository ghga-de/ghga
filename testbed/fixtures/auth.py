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

"""Fixture for testing APIs that use an auth token."""

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from time import sleep
from urllib.parse import parse_qs, urlparse

import pyotp
from ghga_service_commons.utils.utc_dates import now_as_utc
from httpx import Response
from jwcrypto import jwk
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from pyparsing import Any
from pytest import fixture

from fixtures.state import StateStorage

from .config import Config
from .http_client import HttpClient

__all__ = ["auth_fixture"]

DEFAULT_VALID_SECONDS = 60 * 60  # 10 mins
DEFAULT_USER_STATUS = "active"


class Session(BaseModel):
    """Session object that is passed to the client."""

    model_config = ConfigDict(populate_by_name=True)

    user_id: str | None = Field(None, alias="id")
    session_id: str
    csrf: str
    ext_id: str
    name: str
    email: EmailStr
    state: str
    timeout: int
    extends: int
    roles: list[str] | None = None
    # role: str | None = None

    @model_validator(mode="after")
    def assign_ext_id_to_id(self):
        """If ID is not provided, assign the ext_id value.

        Internal ID is assigned when the user is registered,
        until then external ID is used.
        """
        if self.user_id is None:
            self.user_id = self.ext_id
        return self


class TOTPAlgorithm(StrEnum):
    """Hash algorithm used for TOTP code generation"""

    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class TokenGenerator:
    """Generator for auth tokens"""

    black_box_mode: bool
    key_file: Path
    auth_adapter_url: str
    op_url: str
    op_issuer: str
    titles = ("Dr.", "Prof.")
    user_domain = "home.org"

    def __init__(self, config: Config, http: HttpClient):
        self.black_box_mode = config.black_box_mode
        self.key_file = config.auth_key_file
        self.op_url = config.op_url
        self.op_issuer = config.op_issuer
        self.auth_adapter_url = config.ums_url
        if config.api_ext_path:
            self.auth_adapter_url = f"{self.auth_adapter_url}{config.api_ext_path}"
        self.http = http
        if config.totp_algorithm == TOTPAlgorithm.SHA1:
            self.digest = hashlib.sha1
        elif config.totp_algorithm == TOTPAlgorithm.SHA256:
            self.digest = hashlib.sha256
        elif config.totp_algorithm == TOTPAlgorithm.SHA512:
            self.digest = hashlib.sha512
        self.totp_digits = config.totp_digits
        self.totp_interval = config.totp_interval
        self.totp_tolerance = config.totp_tolerance

    @classmethod
    def split_title(cls, full_name: str) -> tuple[str | None, str]:
        """Split the full name into title and actual name."""
        if full_name.startswith(cls.titles):
            title, name = full_name.split(None, 1)
        else:
            title, name = None, full_name
        return title, name

    @classmethod
    def get_initials(cls, full_name: str) -> str | None:
        """Transform the given name to its initials."""
        _, name = cls.split_title(full_name)
        name_parts = name.split()
        if not name_parts:
            return None
        initials = name_parts[0][0].upper()
        if len(name_parts) > 1:
            initials += name_parts[-1][0].upper()
        return initials or None

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
        if full_name == "Central Data Steward":
            return "central@test.dev"
        name = self.split_title(full_name)[1].lower().replace(" ", ".")
        return f"{name}@{self.user_domain}"

    def headers(self, session: Session | None) -> dict[str, str]:
        """Get proper headers for the given session."""
        if not session:
            return {}
        return {
            "X-CSRF-Token": session.csrf,
            "Cookie": f"session={session.session_id}",
        }

    def session_from_response(
        self, response: Response, session_id: str | None = None
    ) -> Session:
        """Get a session object from the response."""
        if not session_id:
            session_id = response.cookies.get("session")
        assert session_id
        session_header = response.headers.get("X-Session")
        assert session_header
        session_dict = json.loads(session_header)
        session = Session(session_id=session_id, **session_dict)
        return session

    def get_saved_session(self, name: str, state_store: StateStorage) -> Session | None:
        """Check state store and get session for the user"""
        sub = self.get_sub(name)
        assert state_store, "No state store provided. Cannot query session."
        session = state_store.get_state(f"session-{sub}") or None
        return Session(**session) if session else None

    def fetch_session(
        self,
        name: str,
        email: str | None = None,
        title: str | None = None,
        user_id: str | None = None,
        valid_seconds: int = DEFAULT_VALID_SECONDS,
        state_store: StateStorage | None = None,
    ) -> Session:
        """Fetch the current session.

        If the session ID is not known, the user is logged in
        using an external access token.
        """
        if title is None:
            title, name = self.split_title(name)
        sub = user_id if user_id else self.get_sub(name)

        session_id = None
        if state_store:
            session = self.get_saved_session(name, state_store)
            if session:
                auth_headers = self.headers(session)
                response = self.auth_login(headers=auth_headers)
                session_id = session.session_id

        if not session_id:
            if state_store:
                all_changed_user_data = state_store.get_state("changed user data") or {}
                changed_user_data = all_changed_user_data.get(sub, {})
                changed_email = changed_user_data.get("email")
                if changed_email:
                    email = changed_email
            external_token = self.oidc_login(
                name=name, email=email, sub=sub, valid_seconds=valid_seconds
            )
            auth_headers = {"Authorization": f"Bearer {external_token}"}

        response = self.auth_login(headers=auth_headers)
        session = self.session_from_response(response, session_id=session_id)
        return session

    def save_session(self, name: str, session: Session, state_store: StateStorage):
        """Memorize the session for the user with the given name."""
        sub = self.get_sub(name)
        session_dict = session.model_dump()
        assert state_store, "No state store provided. Cannot query session."
        state_store.set_state(f"session-{sub}", session_dict)
        state_store.set_state("logged in as", sub)

    def oidc_login(
        self,
        name: str,
        email: str | None = None,
        sub: str | None = None,
        valid_seconds: int | None = None,
    ):
        """Login with OpenID Connect."""
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
        response = self.http.post(url, json=login_info)
        status_code = response.status_code
        assert status_code == 201, f"{status_code}: {response.text}"
        token = response.text
        assert token and token.count(".") == 2
        return token

    def auth_login(self, headers: dict[str, Any]):
        """Get or create session."""
        url = self.auth_adapter_url + "/rpc/login"
        response = self.http.post(url, headers=headers)
        status_code = response.status_code
        assert (
            status_code != 401 or "Not a valid token: Missing Key" not in response.text
        ), (
            "Cannot validate the access token since it is signed with a different key."
            " Maybe the auth adapter needs to be restarted to fetch the right key."
        )
        assert status_code == 204, f"{status_code}: {response.text}"
        return response

    def add_totp_to_headers(self, totp: str, headers: dict[str, Any]) -> dict[str, Any]:
        """Add TOTP to headers.

        'X-Authorization' header is used to submit the one-time password. Due to ExtAuth
        protocol by default doesn't allow the request body.
        """
        headers["X-Authorization"] = f"Bearer TOTP:{totp}"
        return headers

    def get_totp_token(
        self,
        name: str,
        headers: dict[str, Any],
        state_store: StateStorage,
        force: bool = False,
    ) -> str:
        """Request a valid TOTP token."""
        sub = self.get_sub(name)
        if not force:
            assert state_store, "No state store provided. Cannot query TOTP token."
            token = state_store.get_state(f"totp-token-{sub}")
            # Note: This can be used only once unless we wait for 30 seconds.
            if token:
                return token
        url = self.auth_adapter_url + "/totp-token"
        response = self.http.post(url, headers=headers, params={"force": force})
        status_code = response.status_code
        if status_code in (401, 403):
            detail = response.json()["detail"]
            return f"error: {detail}"
        assert status_code == 201, f"{status_code}, {response.text}"
        uri = response.json().get("uri")
        assert uri
        uri_params = parse_qs(urlparse(uri).query)
        assert "secret" in uri_params
        token = uri_params["secret"][0]
        state_store.set_state(f"totp-token-{sub}", token)
        sleep(0.25)  # give the backend some time to store the token
        return token

    def generate_totp(
        self, token: str, for_time: datetime | None = None, offset: int = 0
    ) -> str:
        """Generate a TOTP code for testing purposes."""
        totp = pyotp.TOTP(
            token,
            digest=self.digest,
            digits=self.totp_digits,
            interval=self.totp_interval,
        )
        if for_time is None:
            for_time = now_as_utc()
        return totp.at(for_time, offset)

    def generate_wrong_totp(self, totp_token: str) -> str:
        """Generate valid TOTP but with the wrong time window."""
        tolerance = self.totp_tolerance
        tolerated_totps = {
            self.generate_totp(totp_token, offset=offset)
            for offset in range(-tolerance, tolerance + 1)
        }
        offset = tolerance - 1
        while True:
            wrong_code = self.generate_totp(totp_token, offset=offset)
            if wrong_code not in tolerated_totps:
                return wrong_code
            offset -= 1

    def verify_totp(self, totp: str, headers: dict[str, Any]) -> Response:
        """Verify the TOTP code."""
        url = self.auth_adapter_url + "/rpc/verify-totp"
        headers = self.add_totp_to_headers(totp, headers)
        return self.http.post(url, headers=headers)

    def auth_logout(self, session: Session):
        """Logout and remove session."""
        url = self.auth_adapter_url + "/rpc/logout"
        session_headers = self.headers(session)
        response = self.http.post(url, headers=session_headers)
        status_code = response.status_code
        assert status_code == 204, status_code

    def authenticate(
        self,
        session: Session,
        state_store: StateStorage,
        recreate_totp: bool = False,
    ) -> Response:
        """Authenticate with two-factor authentication."""
        session_headers = self.headers(session)
        # Login to retrieve up-to-date session information from the server
        response = self.auth_login(session_headers)
        session_header = response.headers.get("X-Session")
        assert session_header
        session_dict = json.loads(session_header)
        state = session_dict.get("state")
        if state == "Authenticated":
            return Response(204, content=b"")
        # if session state is not "Authenticated", then we need to authenticate
        totp_token = self.get_totp_token(
            name=session.name,
            headers=session_headers,
            state_store=state_store,
            force=recreate_totp,
        )
        assert not totp_token.startswith("error:"), (
            f"Cannot authenticate {session.name}: {totp_token}"
        )
        totp = self.generate_totp(totp_token)
        return self.verify_totp(totp, session_headers)

    @property
    def key(self) -> jwk.JWK:
        """Read the signing key from a local env file."""
        with open(self.key_file, encoding="ascii") as key_file:
            for line in key_file:
                if line.startswith("AUTH_SERVICE_AUTH_KEY="):
                    return jwk.JWK.from_json(line.split("=", 1)[1].rstrip().strip("'"))
        raise RuntimeError("Cannot read signing key for authentication")


@fixture(name="auth", scope="session")
def auth_fixture(config: Config, http: HttpClient) -> TokenGenerator:
    """Fixture that provides an auth token generator."""
    return TokenGenerator(config, http)
