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

"""Unit tests for the utils module."""

from datetime import timedelta
from typing import cast

import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc

from auth_service.user_management.claims_repository.core.utils import (
    get_active_roles,
    iva_is_verified,
    user_exists,
    user_is_active,
    user_with_iva_exists,
)
from auth_service.user_management.claims_repository.ports.dao import ClaimDao
from auth_service.user_management.user_registry.models.ivas import (
    Iva,
    IvaState,
    IvaType,
)
from auth_service.user_management.user_registry.models.users import UserStatus
from auth_service.user_management.user_registry.ports.dao import IvaDao, UserDao

from ....fixtures.utils import DummyClaimDao, DummyIvaDao, DummyUserDao

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.parametrize("status", [UserStatus.ACTIVE, UserStatus.INACTIVE])
async def test_user_exists(status: UserStatus):
    """Test that existence of users can be checked."""
    user_dao = cast(UserDao, DummyUserDao(id_="some-internal-id", status=status))
    assert await user_exists(None, user_dao=user_dao) is False  # type: ignore
    assert await user_exists("some-internal-id", user_dao=user_dao) is True
    assert await user_exists("other-internal-id", user_dao=user_dao) is False


@pytest.mark.parametrize("status", [UserStatus.ACTIVE, UserStatus.INACTIVE])
async def test_active_user_exists(status: UserStatus):
    """Test that existence of active users can be checked."""
    user_dao = cast(UserDao, DummyUserDao(id_="some-internal-id", status=status))
    assert await user_is_active(None, user_dao=user_dao) is False  # type: ignore
    assert await user_is_active("some-internal-id", user_dao=user_dao) is (
        status == UserStatus.ACTIVE
    )
    assert await user_is_active("other-internal-id", user_dao=user_dao) is False


async def test_iva_exists():
    """Test that existence of IVAs for users can be checked."""
    user_id, iva_id = "some-user-id", "some-iva-id"
    now = now_as_utc()
    iva = Iva(
        id=iva_id,
        user_id=user_id,
        value="123/456",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    kwargs = {
        "user_dao": DummyUserDao(id_=user_id),
        "iva_dao": DummyIvaDao([iva]),
    }

    assert await user_with_iva_exists(None, None, **kwargs) is False  # type: ignore
    assert await user_with_iva_exists(None, iva_id, **kwargs) is False  # type: ignore
    assert await user_with_iva_exists(user_id, None, **kwargs) is False  # type: ignore
    assert await user_with_iva_exists("other-user-id", iva_id, **kwargs) is False  # type: ignore
    assert await user_with_iva_exists(user_id, "other-iva-id", **kwargs) is False  # type: ignore

    assert await user_with_iva_exists(user_id, iva_id, **kwargs) is True  # type: ignore


async def test_iva_exists_when_it_belongs_to_a_different_user():
    """Test that existence and ownership of IVAs for users are properly checked."""
    user_id, iva_id = "some-user-id", "some-iva-id"
    now = now_as_utc()
    iva = Iva(
        id=iva_id,
        user_id="other-user-id",
        value="123/456",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    kwargs = {
        "user_dao": DummyUserDao(id_=user_id),
        "iva_dao": DummyIvaDao([iva]),
    }

    assert await user_with_iva_exists(user_id, iva_id, **kwargs) is False  # type: ignore
    assert await user_with_iva_exists("other-user-id", iva_id, **kwargs) is False  # type: ignore


@pytest.mark.parametrize("state", IvaState)
async def test_iva_is_verified(state: IvaState):
    """Test that existence of verified IVAs for users can be checked."""
    user_id, iva_id = "some-user-id", "some-iva-id"
    now = now_as_utc()
    iva = Iva(
        id=iva_id,
        user_id=user_id,
        value="123/456",
        type=IvaType.PHONE,
        state=state,
        created=now,
        changed=now,
    )
    kwargs = {
        "iva_dao": cast(IvaDao, DummyIvaDao([iva])),
    }

    assert await iva_is_verified(None, None, **kwargs) is False  # type: ignore
    assert await iva_is_verified(None, iva_id, **kwargs) is False  # type: ignore
    assert await iva_is_verified(user_id, None, **kwargs) is False
    assert await iva_is_verified("other-user-id", iva_id, **kwargs) is False
    assert await iva_is_verified(user_id, "other-iva-id", **kwargs) is False
    expected_verified = state == IvaState.VERIFIED
    assert await iva_is_verified(user_id, iva_id, **kwargs) is expected_verified


@pytest.mark.parametrize("state", IvaState)
async def test_get_active_roles_with_iva(state: IvaState):
    """Internal role claims must have an IVA that is in the verified state."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    now = now_as_utc()
    iva = Iva(
        id="data-steward-iva-id",
        user_id=user_id,
        value="123/456",
        type=IvaType.PHONE,
        state=state,
        created=now,
        changed=now,
    )
    iva_dao = cast(IvaDao, DummyIvaDao([iva]))
    expected_roles = ["data_steward"] if state == IvaState.VERIFIED else []
    assert (
        await get_active_roles(
            user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
        )
        == expected_roles
    )


async def test_get_active_roles_deduplicates_roles():
    """Internal role claims are deduplicated."""
    user_id = "james@ghga.de"
    iva_id = "some-iva-id"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())

    now = now_as_utc()
    iva = Iva(
        id=iva_id,
        user_id=user_id,
        value="foo",
        type=IvaType.IN_PERSON,
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    iva_dao = cast(IvaDao, DummyIvaDao([iva]))

    # add claims with 3 different roles (one unsupported) each 3 times
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert claim.visa_value == "data_steward@some.org"

    for i in range(3):
        for role in ["data_steward", "bad_role", "admin"]:
            await claim_dao.insert(
                claim.model_copy(
                    update={
                        "id": f"add-claim-id-{role}-{i + 1}",
                        "iva_id": iva_id,
                        "visa_value": f"{role}@some.org",
                    }
                )
            )

    # we should only get the 2 supported roles, and each only once
    assert await get_active_roles(
        user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    ) == ["admin", "data_steward"]


async def test_get_active_roles_without_iva_id():
    """Active internal role claims must have an associated IVA ID."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert claim.iva_id == "data-steward-iva-id"
    await claim_dao.update(claim.model_copy(update={"iva_id": None}))
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert not claim.iva_id
    iva_dao = cast(IvaDao, DummyIvaDao())
    active_roles = await get_active_roles(
        user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )
    assert active_roles == []


async def test_get_active_roles_with_non_existing_iva():
    """Active internal role claims must have an existing IVA."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao([]))
    active_roles = await get_active_roles(
        user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )
    assert active_roles == []


async def test_get_active_roles_with_wrong_claim():
    """Active internal role claims must have the proper type."""
    user_id = "john@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())
    active_roles = await get_active_roles(
        user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )
    assert active_roles == []


async def test_get_active_roles_with_expired_claim():
    """Active internal role claims must not be expired."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    now = now_as_utc()
    assert claim.valid_from <= now <= claim.valid_until
    assert await get_active_roles(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
        now=lambda: now,
    ) == ["data_steward"]
    assert (
        await get_active_roles(
            user_id,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
            now=lambda: claim.valid_from - timedelta(1),
        )
        == []
    )
    assert (
        await get_active_roles(
            user_id,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
            now=lambda: claim.valid_until + timedelta(1),
        )
        == []
    )


async def test_get_active_roles_with_revoked_claim():
    """Active internal role claims must not have been revoked."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    assert await get_active_roles(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
    ) == ["data_steward"]

    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert claim.revocation_date is None
    await claim_dao.update(claim.model_copy(update={"revocation_date": now_as_utc()}))
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert claim.revocation_date

    assert (
        await get_active_roles(
            user_id,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
        )
        == []
    )


async def test_get_active_roles_with_non_existing_user():
    """Active internal role claims must have an associated user."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    assert await get_active_roles(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
    ) == ["data_steward"]

    user_dao = cast(UserDao, DummyUserDao(id_="jane@ghga.de"))
    assert (
        await get_active_roles(
            user_id,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
        )
        == []
    )


@pytest.mark.parametrize("status", UserStatus)
async def test_get_active_role_with_inactive_user(status: UserStatus):
    """Active internal roles must have an active user status."""
    user_id = "james@ghga.de"
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    for status in UserStatus:
        user_dao = cast(UserDao, DummyUserDao(id_=user_id, status=status))
        expected_roles = ["data_steward"] if status == UserStatus.ACTIVE else []
        assert (
            await get_active_roles(
                user_id,
                user_dao=user_dao,
                iva_dao=iva_dao,
                claim_dao=claim_dao,
            )
            == expected_roles
        )
