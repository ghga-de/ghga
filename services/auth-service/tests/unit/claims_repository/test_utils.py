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

"""Unit tests for the utils module."""

from datetime import timedelta
from typing import Any, cast
from uuid import uuid4

import pytest
from hexkit.utils import now_utc_ms_prec

from auth_service.claims_repository.core.utils import (
    get_active_roles,
    iva_is_verified,
    user_exists,
    user_is_active,
    user_with_iva_exists,
    with_added_roles,
)
from auth_service.claims_repository.ports.dao import ClaimDao
from auth_service.user_registry.models.ivas import (
    Iva,
    IvaState,
    IvaType,
)
from auth_service.user_registry.models.users import UserStatus, UserWithRoles
from auth_service.user_registry.ports.dao import IvaDao, UserDao
from tests.fixtures.constants import (
    DATA_STEWARD_CLAIM_ID,
    DATA_STEWARD_IVA_ID,
    ID_OF_JAMES,
    ID_OF_JOHN,
    SOME_IVA_ID,
    SOME_USER_ID,
)

from ...fixtures.utils import DummyClaimDao, DummyIvaDao, DummyUserDao

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.parametrize("status", [UserStatus.ACTIVE, UserStatus.INACTIVE])
async def test_user_exists(status: UserStatus):
    """Test that existence of users can be checked."""
    user_dao = cast(UserDao, DummyUserDao(id_=SOME_USER_ID, status=status))
    assert not await user_exists(None, user_dao=user_dao)  # type: ignore
    assert await user_exists(SOME_USER_ID, user_dao=user_dao)
    assert not await user_exists(uuid4(), user_dao=user_dao)


@pytest.mark.parametrize("status", [UserStatus.ACTIVE, UserStatus.INACTIVE])
async def test_active_user_exists(status: UserStatus):
    """Test that existence of active users can be checked."""
    user_dao = cast(UserDao, DummyUserDao(id_=SOME_USER_ID, status=status))
    assert not await user_is_active(None, user_dao=user_dao)  # type: ignore
    assert await user_is_active(SOME_USER_ID, user_dao=user_dao) is (
        status == UserStatus.ACTIVE
    )
    assert not await user_is_active(uuid4(), user_dao=user_dao)


async def test_iva_exists():
    """Test that existence of IVAs for users can be checked."""
    now = now_utc_ms_prec()
    iva = Iva(
        id=SOME_IVA_ID,
        user_id=SOME_USER_ID,
        value="123/456",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    kwargs = {
        "user_dao": DummyUserDao(id_=SOME_USER_ID),
        "iva_dao": DummyIvaDao([iva]),
    }

    assert not await user_with_iva_exists(None, None, **kwargs)  # type: ignore
    assert not await user_with_iva_exists(None, SOME_IVA_ID, **kwargs)  # type: ignore
    assert not await user_with_iva_exists(SOME_USER_ID, None, **kwargs)  # type: ignore
    assert not await user_with_iva_exists(uuid4(), SOME_IVA_ID, **kwargs)  # type: ignore
    assert not await user_with_iva_exists(SOME_USER_ID, uuid4(), **kwargs)  # type: ignore

    assert await user_with_iva_exists(SOME_USER_ID, SOME_IVA_ID, **kwargs)  # type: ignore


async def test_iva_exists_when_it_belongs_to_a_different_user():
    """Test that existence and ownership of IVAs for users are properly checked."""
    now = now_utc_ms_prec()
    iva = Iva(
        id=SOME_IVA_ID,
        user_id=uuid4(),
        value="123/456",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    kwargs: Any = {
        "user_dao": DummyUserDao(id_=SOME_USER_ID),
        "iva_dao": DummyIvaDao([iva]),
    }

    assert not await user_with_iva_exists(SOME_USER_ID, SOME_IVA_ID, **kwargs)
    assert not await user_with_iva_exists(iva.user_id, SOME_IVA_ID, **kwargs)


@pytest.mark.parametrize("state", IvaState)
async def test_iva_is_verified(state: IvaState):
    """Test that existence of verified IVAs for users can be checked."""
    now = now_utc_ms_prec()
    iva = Iva(
        id=SOME_IVA_ID,
        user_id=SOME_USER_ID,
        value="123/456",
        type=IvaType.PHONE,
        state=state,
        created=now,
        changed=now,
    )
    kwargs = {
        "iva_dao": cast(IvaDao, DummyIvaDao([iva])),
    }

    assert not await iva_is_verified(None, None, **kwargs)  # type: ignore
    assert not await iva_is_verified(None, SOME_IVA_ID, **kwargs)  # type: ignore
    assert not await iva_is_verified(SOME_USER_ID, None, **kwargs)
    assert not await iva_is_verified(uuid4(), SOME_IVA_ID, **kwargs)
    assert not await iva_is_verified(SOME_USER_ID, uuid4(), **kwargs)
    expected_verified = state == IvaState.VERIFIED
    assert (
        await iva_is_verified(SOME_USER_ID, SOME_IVA_ID, **kwargs) is expected_verified
    )


async def test_get_active_roles_without_iva():
    """Internal role claims without IVA can be requested."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    expected_roles = ["data_steward"]
    assert (
        await get_active_roles(ID_OF_JAMES, user_dao=user_dao, claim_dao=claim_dao)
        == expected_roles
    )


@pytest.mark.parametrize("state", IvaState)
async def test_get_active_roles_with_iva(state: IvaState):
    """Internal role claims must have an IVA that is in the verified state."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    now = now_utc_ms_prec()
    iva = Iva(
        id=DATA_STEWARD_IVA_ID,
        user_id=ID_OF_JAMES,
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
            ID_OF_JAMES, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
        )
        == expected_roles
    )


async def test_get_active_roles_deduplicates_roles():
    """Internal role claims are deduplicated."""
    iva_id = SOME_IVA_ID
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())

    now = now_utc_ms_prec()
    iva = Iva(
        id=iva_id,
        user_id=ID_OF_JAMES,
        value="foo",
        type=IvaType.IN_PERSON,
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    iva_dao = cast(IvaDao, DummyIvaDao([iva]))

    # add claims with 3 different roles (one unsupported) each 3 times
    claim = await claim_dao.get_by_id(DATA_STEWARD_CLAIM_ID)
    assert claim.visa_value == "data_steward@some.org"

    for _ in range(3):
        for role in ["data_steward", "bad_role", "admin"]:
            await claim_dao.insert(
                claim.model_copy(
                    update={
                        "id": uuid4(),
                        "iva_id": iva_id,
                        "visa_value": f"{role}@some.org",
                    }
                )
            )

    # we should only get the 2 supported roles, and each only once
    assert await get_active_roles(
        ID_OF_JAMES, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    ) == ["admin", "data_steward"]


async def test_get_active_roles_without_iva_id():
    """Active internal role claims must have an associated IVA ID."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    claim = await claim_dao.get_by_id(DATA_STEWARD_CLAIM_ID)
    assert claim.iva_id == DATA_STEWARD_IVA_ID
    await claim_dao.update(claim.model_copy(update={"iva_id": None}))
    claim = await claim_dao.get_by_id(DATA_STEWARD_CLAIM_ID)
    assert not claim.iva_id
    iva_dao = cast(IvaDao, DummyIvaDao())
    active_roles = await get_active_roles(
        ID_OF_JAMES, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )
    assert active_roles == []


async def test_get_active_roles_with_non_existing_iva():
    """Active internal role claims must have an existing IVA."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao([]))
    active_roles = await get_active_roles(
        ID_OF_JAMES, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )
    assert active_roles == []


async def test_get_active_roles_with_wrong_claim():
    """Active internal role claims must have the proper type."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JOHN))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())
    active_roles = await get_active_roles(
        ID_OF_JOHN, user_dao=user_dao, iva_dao=iva_dao, claim_dao=claim_dao
    )
    assert active_roles == []


async def test_get_active_roles_with_expired_claim():
    """Active internal role claims must not be expired."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())
    claim = await claim_dao.get_by_id(DATA_STEWARD_CLAIM_ID)
    now = now_utc_ms_prec()
    assert claim.valid_from <= now <= claim.valid_until
    assert await get_active_roles(
        ID_OF_JAMES,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
        now=lambda: now,
    ) == ["data_steward"]
    assert (
        await get_active_roles(
            ID_OF_JAMES,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
            now=lambda: claim.valid_from - timedelta(1),
        )
        == []
    )
    assert (
        await get_active_roles(
            ID_OF_JAMES,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
            now=lambda: claim.valid_until + timedelta(1),
        )
        == []
    )


async def test_get_active_roles_with_revoked_claim():
    """Active internal role claims must not have been revoked."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    assert await get_active_roles(
        ID_OF_JAMES,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
    ) == ["data_steward"]

    claim = await claim_dao.get_by_id(DATA_STEWARD_CLAIM_ID)
    assert claim.revocation_date is None
    await claim_dao.update(
        claim.model_copy(update={"revocation_date": now_utc_ms_prec()})
    )
    claim = await claim_dao.get_by_id(DATA_STEWARD_CLAIM_ID)
    assert claim.revocation_date

    assert (
        await get_active_roles(
            ID_OF_JAMES,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
        )
        == []
    )


async def test_get_active_roles_with_non_existing_user():
    """Active internal role claims must have an associated user."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    assert await get_active_roles(
        ID_OF_JAMES,
        user_dao=user_dao,
        iva_dao=iva_dao,
        claim_dao=claim_dao,
    ) == ["data_steward"]

    user_dao = cast(UserDao, DummyUserDao(id_=SOME_USER_ID))
    assert (
        await get_active_roles(
            ID_OF_JAMES,
            user_dao=user_dao,
            iva_dao=iva_dao,
            claim_dao=claim_dao,
        )
        == []
    )


@pytest.mark.parametrize("status", UserStatus)
async def test_get_active_role_with_inactive_user(status: UserStatus):
    """Active internal roles must have an active user status."""
    claim_dao = cast(ClaimDao, DummyClaimDao())
    iva_dao = cast(IvaDao, DummyIvaDao())

    for status in UserStatus:
        user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES, status=status))
        expected_roles = ["data_steward"] if status == UserStatus.ACTIVE else []
        assert (
            await get_active_roles(
                ID_OF_JAMES,
                user_dao=user_dao,
                iva_dao=iva_dao,
                claim_dao=claim_dao,
            )
            == expected_roles
        )


async def test_empty_user_list_with_added_roles():
    """Adding roles works with an empty list of users."""
    claim_dao = cast(ClaimDao, DummyClaimDao())
    assert await with_added_roles([], claim_dao=claim_dao) == []


async def test_non_empty_user_list_with_added_roles():
    """The proper roles are added to a non-empty list of users."""
    user_dao = cast(UserDao, DummyUserDao(id_=ID_OF_JAMES))
    claim_dao = cast(ClaimDao, DummyClaimDao())
    user = await user_dao.get_by_id(ID_OF_JAMES)
    user_with_roles = UserWithRoles(
        **user.model_dump(),
        roles=["data_steward"],
    )
    assert await with_added_roles([user], claim_dao=claim_dao) == [user_with_roles]
