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

"""Logic for authorization using alphanumeric tokens."""

import secrets
from hashlib import sha256


def generate_token() -> str:
    """Generate a random token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash the given token."""
    return sha256(token.encode()).hexdigest()


def generate_token_and_hash() -> tuple[str, str]:
    """Generate a random token and its hash."""
    token = generate_token()
    token_hash = hash_token(token)
    return token, token_hash


def check_token(token: str, token_hashes: list[str]) -> bool:
    """Check whether the given token matches one of the given token hashes."""
    return hash_token(token) in token_hashes
