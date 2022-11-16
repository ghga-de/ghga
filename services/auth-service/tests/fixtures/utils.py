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

"""Utils for testing"""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Mapping, Optional

from hexkit.protocols.dao import NoHitsFoundError, ResourceNotFoundError
from jwcrypto import jwk, jwt

from auth_service.auth_adapter.core.auth import jwt_config
from auth_service.config import CONFIG
from auth_service.user_management.claims_repository.models.dto import (
    AuthorityLevel,
    Claim,
    VisaType,
)
from auth_service.user_management.user_registry.models.dto import User, UserStatus
from auth_service.user_management.utils import DateTimeUTC, now_as_utc

BASE_DIR = Path(__file__).parent.resolve()


def create_access_token(
    key: Optional[jwk.JWK] = None, expired: bool = False, **kwargs
) -> str:
    """Create an external access token that can be used for testing.

    If no signing key is provided, the external_jwks from the global jwt_config is used.
    """
    if not key:
        keyset = jwt_config.external_jwks
        assert isinstance(keyset, jwk.JWKSet)
        key = keyset.get_key("test")
    assert isinstance(key, jwk.JWK)
    kty = key["kty"]
    assert kty in ("EC", "RSA")
    header = {"alg": "ES256" if kty == "EC" else "RS256", "typ": "JWT"}
    claims = jwt_config.check_claims.copy()
    claims.update(
        name="John Doe",
        email="john@home.org",
        jti="1234567890",
        sub="john@aai.org",
        foo="bar",
    )
    iat = int(now_as_utc().timestamp())
    exp = iat + 60
    if expired:
        iat -= 120
        exp -= 120
    claims.update(iat=iat, exp=exp)
    claims.update(kwargs)
    token = jwt.JWT(header=header, claims=claims)
    token.make_signed_token(key)
    access_token = token.serialize()
    assert token and isinstance(access_token, str)
    assert len(access_token) > 50
    assert access_token.count(".") == 2
    return access_token


def get_claims_from_token(token: str, key: Optional[jwk.JWK] = None) -> dict[str, Any]:
    """Decode the given JWT token and get its claims.

    If no signing key is provided, the internal_jwk from the global jwt_config is used.
    """
    if not key:
        key = jwt_config.internal_jwk
    assert isinstance(key, jwk.JWK)
    assert token and isinstance(token, str)
    assert len(token) > 50
    assert token.count(".") == 2
    claims = json.loads(jwt.JWT(jwt=token, key=key).claims)
    assert isinstance(claims, dict)
    return claims


class DummyUserDao:
    """UserDao that can retrieve one dummy user."""

    def __init__(
        self,
        id_="john@ghga.de",
        name="John Doe",
        email="john@home.org",
        ls_id="john@aai.org",
    ):
        """Initialize the dummy UserDao"""
        self.user = User(
            id=id_,
            name=name,
            email=email,
            ls_id=ls_id,
            status=UserStatus.ACTIVATED,
            status_change=None,
            registration_date=DateTimeUTC.create(2020, 1, 1),
        )

    async def get_by_id(self, id_: str) -> User:
        """Get the dummy user via internal ID."""
        if id_ == self.user.id:
            return self.user
        raise ResourceNotFoundError(id_=id_)

    async def find_one(self, *, mapping: Mapping[str, Any]) -> Optional[User]:
        """Find the dummy user via LS-ID."""
        user, ls_id = self.user, mapping.get("ls_id")
        if user and ls_id and ls_id == user.ls_id:
            return user
        raise NoHitsFoundError(mapping=mapping)

    async def update(self, user: User) -> None:
        """Update the dummy user."""
        if user.id == self.user.id:
            self.user = user


class DummyClaimDao:
    """ClaimDao that can retrieve a dummy data steward claim."""

    def __init__(self, valid_date=now_as_utc()):
        """Initialize the dummy ClaimDao"""
        self.valid_date = valid_date
        self.invalid_date = valid_date + timedelta(14)
        self.claim = Claim(
            id="dummy-claim-id",
            user_id="james@ghga.de",
            visa_type=VisaType.GHGA_ROLE,
            visa_value="data_steward@some.org",
            source=CONFIG.organization_url,
            assertion_date=valid_date - timedelta(14),
            asserted_by=AuthorityLevel.SYSTEM,
            valid_from=valid_date - timedelta(7),
            valid_until=valid_date + timedelta(7),
            creation_date=valid_date - timedelta(10),
            creation_by="maria@ghga.de",
        )

    async def get_by_id(self, id_: str) -> Claim:
        """Get the dummy user claim via its ID."""
        if id_ == self.claim.id:
            return self.claim
        raise ResourceNotFoundError(id_=id_)

    async def find_all(self, *, mapping: Mapping[str, Any]) -> AsyncIterator[Claim]:
        """Find all dummy user claims."""
        claim = self.claim
        claim_id, user_id, visa_type = claim.id, claim.user_id, claim.visa_type
        if (
            mapping.get("id", claim_id) == claim_id
            and mapping.get("user_id", user_id) == user_id
            and mapping.get("visa_type", visa_type) == visa_type
        ):
            yield claim
