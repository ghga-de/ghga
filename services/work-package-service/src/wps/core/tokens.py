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

"""Management of access tokens and work order tokens"""

import hashlib
import secrets
import string

from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token
from jwcrypto import jwk

from wps.core.models import WorkOrderToken

__all__ = [
    "generate_work_package_access_token",
    "hash_token",
    "sign_work_order_token",
]


ACCESS_TOKEN_CHARSET = string.ascii_letters + string.digits
ACCESS_TOKEN_LENGTH = 24
WORK_ORDER_TOKEN_VALID_SECONDS = 30


def generate_work_package_access_token() -> str:
    """Create a random access token consisting of ascii letters and digits."""
    return "".join(
        secrets.choice(ACCESS_TOKEN_CHARSET) for _ in range(ACCESS_TOKEN_LENGTH)
    )


def hash_token(token: str) -> str:
    """Create a SHA-256 hash of the given token string as hex string."""
    return hashlib.sha256(token.encode()).hexdigest()


def sign_work_order_token(
    work_order_token: WorkOrderToken,
    key: jwk.JWK,
    valid_seconds: int = WORK_ORDER_TOKEN_VALID_SECONDS,
):
    """Sign the given work order token."""
    claims = work_order_token.model_dump()
    return sign_and_serialize_token(claims, key=key, valid_seconds=valid_seconds)
