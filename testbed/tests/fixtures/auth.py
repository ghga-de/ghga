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

from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token
from jwcrypto import jwk
from pytest import fixture

__all__ = ["auth_fixture"]

DEFAULT_VALID_SECONDS = 60 * 10  # 10 mins
DEFAULT_USER_STATUS = "active"

KEY_FILE = Path(__file__).parent.parent.parent / ".devcontainer/auth.env"


class TokenGenerator:
    """Generator for internal auth tokens"""

    key: jwk.JWK

    def __init__(self):
        self.key = self.read_key()

    def generate_headers(
        self,
        *,
        name: str,
        email: str,
        title: Optional[str] = None,
        id_: Optional[str] = None,
        role: Optional[str] = None,
        status: str = DEFAULT_USER_STATUS,
        valid_seconds: int = DEFAULT_VALID_SECONDS,
    ) -> dict[str, str]:
        """Generate headers with internal auth token with specified claims."""
        claims = {
            "id": id_,
            "name": name,
            "email": email,
            "title": title,
            "role": role,
            "status": status,
        }
        token = sign_and_serialize_token(claims, self.key, valid_seconds)
        return {"Authorization": f"Bearer {token}"}

    def read_key(self) -> jwk.JWK:
        """Read the signing key from a local env file."""
        with open(KEY_FILE, encoding="ascii") as key_file:
            for line in key_file:
                if line.startswith("AUTH_KEY="):
                    return jwk.JWK.from_json(line.split("=", 1)[1].rstrip().strip("'"))
        raise RuntimeError("Cannot read signing key for authentication")

    def read_simple_token(self) -> str:
        """Read the simple token from a local env file."""
        with open(KEY_FILE, encoding="ascii") as key_file:
            for line in key_file:
                if line.startswith("SIMPLE_TOKEN="):
                    return line.split("=", 1)[1].rstrip().strip('"')
        raise RuntimeError("Cannot read simple token for authentication")


@fixture(name="auth")
def auth_fixture() -> TokenGenerator:
    """Fixture that provides an internal auth token generator."""

    return TokenGenerator()
