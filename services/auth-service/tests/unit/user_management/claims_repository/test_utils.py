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
    is_data_steward,
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
async def test_is_data_steward_with_iva(state: IvaState):
    """Data steward claim must have an IVA that is in the verified state."""
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
    expected_is_data_steward = state == IvaState.VERIFIED
    assert (
        await is_data_steward(
            user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
        )
        == expected_is_data_steward
    )


async def test_is_data_steward_without_iva_id():
    """Data steward claim must have an associated IVA ID."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert claim.iva_id == "data-steward-iva-id"
    await claim_dao.update(claim.model_copy(update={"iva_id": None}))
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert not claim.iva_id
    iva_dao = cast(IvaDao, DummyIvaDao())
    assert not await is_data_steward(
        user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )


async def test_is_data_steward_with_non_existing_iva():
    """Data steward claim must have an existing IVA."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao([]))
    assert not await is_data_steward(
        user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )


async def test_is_data_steward_with_wrong_claim():
    """Data steward claim must have the proper type."""
    user_id = "john@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())
    assert not await is_data_steward(
        user_id, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )


async def test_is_data_steward_with_expired_claim():
    """Data steward claim must have a claim that is not expired."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    now = now_as_utc()
    assert claim.valid_from <= now <= claim.valid_until
    assert await is_data_steward(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
        now=lambda: now,
    )
    assert not await is_data_steward(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
        now=lambda: claim.valid_from - timedelta(1),
    )
    assert not await is_data_steward(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
        now=lambda: claim.valid_until + timedelta(1),
    )


async def test_is_data_steward_with_revoked_claim():
    """Data steward claim must not have been revoked."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    assert await is_data_steward(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
    )

    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert claim.revocation_date is None
    await claim_dao.update(claim.model_copy(update={"revocation_date": now_as_utc()}))
    claim = await claim_dao.get_by_id("data-steward-claim-id")
    assert claim.revocation_date

    assert not await is_data_steward(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
    )


async def test_is_data_steward_with_non_existing_user():
    """Data steward claim must have an associated user."""
    user_id = "james@ghga.de"
    user_dao = cast(UserDao, DummyUserDao(id_=user_id))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    assert await is_data_steward(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
    )

    user_dao = cast(UserDao, DummyUserDao(id_="jane@ghga.de"))
    assert not await is_data_steward(
        user_id,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
    )


@pytest.mark.parametrize("status", UserStatus)
async def test_is_data_steward_with_inactive_user(status: UserStatus):
    """Data steward must have an active user status."""
    user_id = "james@ghga.de"
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    for status in UserStatus:
        user_dao = cast(UserDao, DummyUserDao(id_=user_id, status=status))
        expected_is_data_steward = status == UserStatus.ACTIVE
        assert (
            await is_data_steward(
                user_id,
                user_dao=user_dao,
                iva_dao=iva_dao,
                claim_dao=claim_dao,
            )
            == expected_is_data_steward
        )
