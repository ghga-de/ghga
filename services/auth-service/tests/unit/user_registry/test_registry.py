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

"""Unit tests for the core user and IVA registry."""

from datetime import timedelta
from uuid import uuid4

import pytest
from hexkit.utils import now_utc_ms_prec

from auth_service.user_registry.core.registry import UserRegistry
from auth_service.user_registry.core.verification_codes import (
    generate_code,
    hash_code,
    validate_code,
)
from auth_service.user_registry.models.ivas import (
    Iva,
    IvaAndUserData,
    IvaBasicData,
    IvaData,
    IvaState,
    IvaType,
)
from auth_service.user_registry.models.users import (
    AcademicTitle,
    UserBasicData,
    UserModifiableData,
    UserRegisteredData,
    UserStatus,
    UserWithRoles,
)
from tests.fixtures.constants import ID_OF_JANE, ID_OF_JOHN, ID_OF_ROD_STEWARD, IVA_IDS

from ...fixtures.utils import MockUserRegistry

pytestmark = pytest.mark.asyncio()

VERIFICATION_CODE_SIZE = 6  # the expected size of verification codes


async def test_is_internal_user_id():
    """Test that internal IDs can be validated."""
    is_internal_id = UserRegistry.is_internal_user_id
    assert is_internal_id(None) is False  # type: ignore
    assert is_internal_id(42) is False  # type: ignore
    assert is_internal_id("") is False
    assert is_internal_id("foo-bar") is False
    assert is_internal_id("foo-bar-baz-qux") is False
    assert is_internal_id("foo@bar.baz") is False
    assert is_internal_id("16fd2706-8baf-433b-82eb-8c7fada847da") is True
    assert is_internal_id("16fd2706-8baf-433b-82eb-8c7f@da847da") is False


async def test_is_external_user_id():
    """Test that internal IDs can be validated."""
    is_external_id = UserRegistry.is_external_user_id
    assert is_external_id(None) is False  # type: ignore
    assert is_external_id(42) is False  # type: ignore
    assert is_external_id("") is False
    assert is_external_id("@") is False
    assert is_external_id("foo@bar.baz") is True
    assert is_external_id("foo@bar@baz") is False
    assert is_external_id("16fd2706-8baf-433b-82eb-8c7fada847da") is False


async def test_create_existing_user():
    """Test creating a user account that already exists."""
    registry = MockUserRegistry()
    user = registry.mock_user_dao.user
    user_data = UserRegisteredData(
        ext_id=user.ext_id, name="John Foo", email="foo@home.org"
    )
    with pytest.raises(
        UserRegistry.UserAlreadyExistsError,
        match=f"Could not create user with external ID {user.ext_id}:"
        " user already exists",
    ):
        await registry.create_user(user_data)


async def test_create_new_user():
    """Test creating a user account that does not yet exist."""
    registry = MockUserRegistry()
    user_data = UserRegisteredData(
        ext_id="jane@aai.org",
        name="Jane Roe",
        title=AcademicTitle.DR,
        email="jane@home.org",
    )
    user = await registry.create_user(user_data)
    user = user.model_copy(update={"id": ID_OF_JANE})
    assert user == UserWithRoles(**registry.dummy_user.model_dump(), roles=[])
    assert registry.is_internal_user_id(str(user.id))
    assert user.ext_id == "jane@aai.org"
    assert user.status == UserStatus.ACTIVE
    assert 0 <= (now_utc_ms_prec() - user.registration_date).total_seconds() < 3


async def test_get_existing_user():
    """Test getting an existing user."""
    registry = MockUserRegistry()
    dummy_user = registry.dummy_user
    user = await registry.get_user(dummy_user.id)
    assert user is dummy_user


async def test_get_non_existing_user():
    """Test trying to get a non-existing user."""
    registry = MockUserRegistry()
    with pytest.raises(
        registry.UserDoesNotExistError,
        match=f"User with ID {ID_OF_JANE} does not exist",
    ):
        await registry.get_user(ID_OF_JANE)


async def test_update_basic_data():
    """Test updating the basic data of an existing user."""
    registry = MockUserRegistry()
    dummy_user = registry.dummy_user
    basic_data = UserBasicData(
        name="John Doe Jr.", email="john@new.home.org", title=AcademicTitle.PROF
    )
    await registry.update_user(dummy_user.id, basic_data)
    assert registry.dummy_user is not dummy_user
    dummy_user = registry.dummy_user
    assert dummy_user.name == "John Doe Jr."
    assert dummy_user.email == "john@new.home.org"
    assert dummy_user.title == AcademicTitle.PROF
    assert dummy_user.status is UserStatus.ACTIVE


async def test_update_modifiable_data_only_title():
    """Test updating just the title of an existing user."""
    registry = MockUserRegistry()
    dummy_user = registry.dummy_user
    basic_data = UserModifiableData(title=AcademicTitle.PROF)
    await registry.update_user(dummy_user.id, basic_data)
    assert registry.dummy_user is not dummy_user
    dummy_user = registry.dummy_user
    assert dummy_user.name == "John Doe"
    assert dummy_user.email == "john@home.org"
    assert dummy_user.title is AcademicTitle.PROF
    assert dummy_user.status is UserStatus.ACTIVE
    assert dummy_user.status_change is None


async def test_update_modifiable_data_only_status():
    """Test updating just the status of an existing user."""
    registry = MockUserRegistry()
    dummy_user = registry.dummy_user
    basic_data = UserModifiableData(status=UserStatus.INACTIVE)
    await registry.update_user(
        dummy_user.id,
        basic_data,
        changed_by=ID_OF_ROD_STEWARD,
        context="This is some context.",
    )
    assert registry.dummy_user is not dummy_user
    dummy_user = registry.dummy_user
    assert dummy_user.name == "John Doe"
    assert dummy_user.email == "john@home.org"
    assert dummy_user.title is None
    assert dummy_user.status is UserStatus.INACTIVE
    status_change = dummy_user.status_change
    assert status_change
    assert status_change.previous is UserStatus.ACTIVE
    assert status_change.by == ID_OF_ROD_STEWARD
    assert status_change.context == "This is some context."
    change_date = status_change.change_date
    assert change_date
    assert 0 <= (now_utc_ms_prec() - change_date).total_seconds() < 3


async def test_update_modifiable_data_title_and_status():
    """Test updating the title and the status of an existing user."""
    registry = MockUserRegistry()
    dummy_user = registry.dummy_user
    basic_data = UserModifiableData(
        status=UserStatus.INACTIVE, title=AcademicTitle.PROF
    )
    await registry.update_user(
        dummy_user.id,
        basic_data,
    )
    assert registry.dummy_user is not dummy_user
    dummy_user = registry.dummy_user
    assert dummy_user.name == "John Doe"
    assert dummy_user.email == "john@home.org"
    assert dummy_user.title is AcademicTitle.PROF
    assert dummy_user.status is UserStatus.INACTIVE
    status_change = dummy_user.status_change
    assert status_change
    assert status_change.previous is UserStatus.ACTIVE
    assert status_change.by is None
    assert status_change.context is None
    change_date = status_change.change_date
    assert change_date
    assert 0 <= (now_utc_ms_prec() - change_date).total_seconds() < 3


async def test_update_non_existing_user():
    """Test updating the basic data of a non-existing user."""
    registry = MockUserRegistry()
    basic_data = UserBasicData(name="John Doe", email="john@home.org")
    with pytest.raises(
        registry.UserDoesNotExistError,
        match=f"User with ID {ID_OF_JANE} does not exist",
    ):
        await registry.update_user(ID_OF_JANE, basic_data)


async def test_delete_existing_user():
    """Test deleting an existing user."""
    registry = MockUserRegistry()
    assert registry.dummy_users
    await registry.delete_user(ID_OF_JOHN)
    assert not registry.dummy_users


async def test_delete_non_existing_user():
    """Test deleting a non-existing user."""
    registry = MockUserRegistry()
    with pytest.raises(
        registry.UserDoesNotExistError,
        match=f"User with ID {ID_OF_JANE} does not exist",
    ):
        await registry.delete_user(ID_OF_JANE)


async def test_delete_existing_user_with_ivas():
    """Test deleting an existing user who has IVAs."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(value="123")
    registry.add_dummy_iva(user_id=ID_OF_JANE, value="456")
    registry.add_dummy_iva(value="789")
    ivas = registry.dummy_ivas
    assert len(ivas) == 3
    await registry.delete_user(ID_OF_JOHN)
    assert not registry.dummy_users
    assert len(ivas) == 1
    assert ivas[0].user_id == ID_OF_JANE


async def test_create_new_iva():
    """Test creating a new IVA."""
    registry = MockUserRegistry()
    iva_data = IvaBasicData(type=IvaType.PHONE, value="123456")
    iva_id = await registry.create_iva(ID_OF_JOHN, iva_data)
    assert iva_id
    ivas = registry.dummy_ivas
    assert isinstance(ivas, list)
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva.id == iva_id
    assert iva.user_id == ID_OF_JOHN
    assert iva.type == IvaType.PHONE
    assert iva.value == "123456"
    assert iva.state == IvaState.UNVERIFIED
    assert iva.verification_code_hash is None
    assert iva.verification_attempts == 0
    assert 0 <= (now_utc_ms_prec() - iva.created).total_seconds() < 3
    assert 0 <= (now_utc_ms_prec() - iva.changed).total_seconds() < 3


async def test_create_iva_for_non_existing_user():
    """Test creating an IVA for a non-existing user."""
    registry = MockUserRegistry()
    iva_data = IvaBasicData(type=IvaType.PHONE, value="123456")
    with pytest.raises(
        registry.UserDoesNotExistError,
        match=f"User with ID {ID_OF_JANE} does not exist",
    ):
        await registry.create_iva(ID_OF_JANE, iva_data)
    assert not registry.published_events


async def test_get_ivas_of_non_existing_user():
    """Test trying to get all IVAs of a non-existing user."""
    registry = MockUserRegistry()
    ivas = await registry.get_ivas(ID_OF_JANE)
    assert isinstance(ivas, list)
    assert not ivas


async def test_get_ivas_of_an_existing_user_without_ivas():
    """Test getting all IVAs of an existing user without IVAS."""
    registry = MockUserRegistry()
    ivas = await registry.get_ivas(ID_OF_JOHN)
    assert isinstance(ivas, list)
    assert not ivas


async def test_get_ivas_of_an_existing_user_with_ivas():
    """Test getting all IVAs of an existing user without IVAS."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(value="123")
    registry.add_dummy_iva(value="456", user_id=ID_OF_JANE)
    registry.add_dummy_iva(value="789")
    ivas_before = list(registry.dummy_ivas)
    assert len(ivas_before) == 3
    ivas = await registry.get_ivas(ID_OF_JOHN)
    assert isinstance(ivas, list)
    assert len(ivas) == 2
    for iva in ivas:
        assert isinstance(iva, IvaData)
    assert [Iva(**iva.model_dump(), user_id=ID_OF_JOHN) for iva in ivas] == [
        iva for iva in ivas_before if iva.user_id == ID_OF_JOHN
    ]
    assert not registry.published_events


async def test_get_ivas_of_an_existing_user_filtering_by_state():
    """Test getting all IVAs of an existing user without IVAS."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(value="123")
    registry.add_dummy_iva(value="456", state=IvaState.VERIFIED)
    ivas = await registry.get_ivas(ID_OF_JOHN)
    assert isinstance(ivas, list)
    assert len(ivas) == 2
    ivas = await registry.get_ivas(ID_OF_JOHN, state=IvaState.VERIFIED)
    assert isinstance(ivas, list)
    assert len(ivas) == 1
    assert ivas[0].state == IvaState.VERIFIED
    ivas = await registry.get_ivas(ID_OF_JOHN, state=IvaState.CODE_REQUESTED)
    assert isinstance(ivas, list)
    assert len(ivas) == 0
    assert not registry.published_events


async def test_get_all_ivas_with_user():
    """Test getting all IVAs with user data."""
    registry = MockUserRegistry()
    john = registry.dummy_user
    jane = john.model_copy(
        update={
            "id": ID_OF_JANE,
            "name": "Jane Roe",
            "title": AcademicTitle.PROF,
            "email": "jane@home.org",
        }
    )
    registry.dummy_users.append(jane)
    registry.add_dummy_iva(value="123", user_id=john.id)
    registry.add_dummy_iva(value="456", user_id=jane.id)
    registry.add_dummy_iva(value="789", user_id=john.id, state=IvaState.VERIFIED)
    expected_ivas_with_users = [
        IvaAndUserData(
            id=iva.id,
            type=iva.type,
            value=iva.value,
            state=iva.state,
            created=iva.created,
            changed=iva.changed,
            user_id=user.id,
            user_name=user.name,
            user_title=user.title,
            user_email=user.email,
        )
        for iva, user in zip(registry.dummy_ivas, [john, jane, john], strict=True)
    ]
    ivas_with_users = await registry.get_ivas_with_users()
    assert ivas_with_users == expected_ivas_with_users
    assert not registry.published_events


async def test_get_selected_ivas_with_user():
    """Test getting a selection of IVAs with user data."""
    registry = MockUserRegistry()
    john = registry.dummy_user
    jane = john.model_copy(update={"id": ID_OF_JANE})
    registry.dummy_users.append(jane)
    add_iva = registry.add_dummy_iva
    add_iva(value="123", user_id=john.id)
    add_iva(value="456", user_id=jane.id)
    add_iva(value="789", user_id=john.id, state=IvaState.VERIFIED)
    get_ivas = registry.get_ivas_with_users
    ivas = await get_ivas(user_id=jane.id)
    assert len(ivas) == 1
    assert ivas[0].value == "456"
    ivas = await get_ivas(state=IvaState.VERIFIED)
    assert len(ivas) == 1
    assert ivas[0].value == "789"
    ivas = await get_ivas(state=IvaState.UNVERIFIED, user_id=john.id)
    assert len(ivas) == 1
    assert ivas[0].value == "123"
    assert not registry.published_events


async def test_delete_existing_iva():
    """Test deleting an existing IVA."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(value="123")
    registry.add_dummy_iva(value="456", user_id=ID_OF_JANE)
    ivas = registry.dummy_ivas
    assert len(ivas) == 2
    await registry.delete_iva(IVA_IDS[1])
    assert len(ivas) == 1
    assert ivas[0].id == IVA_IDS[0]
    await registry.delete_iva(IVA_IDS[0])
    assert not ivas
    assert not registry.published_events


async def test_delete_non_existing_iva():
    """Test deleting a non-existing IVA."""
    registry = MockUserRegistry()
    ivas = registry.dummy_ivas
    registry.add_dummy_iva()
    assert len(ivas) == 1
    with pytest.raises(
        registry.IvaDoesNotExistError, match=f"IVA with ID {IVA_IDS[1]} does not exist"
    ):
        await registry.delete_iva(IVA_IDS[1])
    assert len(ivas) == 1


async def test_delete_iva_for_a_user():
    """Test deleting an IVA for a given user."""
    registry = MockUserRegistry()
    ivas = registry.dummy_ivas
    registry.add_dummy_iva()
    assert len(ivas) == 1
    await registry.delete_iva(IVA_IDS[0], user_id=ID_OF_JOHN)
    assert not ivas
    assert not registry.published_events


async def test_delete_iva_for_nonexisting_user():
    """Test deleting an IVA for a non-existing user."""
    registry = MockUserRegistry()
    ivas = registry.dummy_ivas
    registry.add_dummy_iva()
    assert len(ivas) == 1
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"User with ID {ID_OF_JANE} does not have an IVA with ID {IVA_IDS[0]}",
    ):
        await registry.delete_iva(IVA_IDS[0], user_id=ID_OF_JANE)
    assert len(ivas) == 1
    assert ivas[0].id == IVA_IDS[0]


async def test_delete_iva_for_wrong_user():
    """Test deleting an IVA for the wrong user."""
    registry = MockUserRegistry()
    ivas = registry.dummy_ivas
    registry.add_dummy_iva()
    assert len(ivas) == 1
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"User with ID {ID_OF_JANE} does not have an IVA with ID {IVA_IDS[0]}",
    ):
        await registry.delete_iva(IVA_IDS[0], user_id=ID_OF_JANE)
    assert len(ivas) == 1
    assert ivas[0].id == IVA_IDS[0]


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.UNVERIFIED,
        IvaState.CODE_REQUESTED,
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
        IvaState.VERIFIED,
    ],
)
async def test_unverify_iva(from_state: IvaState):
    """Test that an IVA can be reset to the unverified state."""
    now = now_utc_ms_prec()
    before = now - timedelta(hours=3)
    registry = MockUserRegistry()
    registry.add_dummy_iva(
        state=from_state,
        verification_code_hash="some-hash",
        verification_attempts=3,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    from_iva = ivas[0]
    await registry.unverify_iva(IVA_IDS[0])
    iva = ivas[0]
    changed = iva.changed
    assert 0 <= (changed - now).total_seconds() < 3
    expected_iva = from_iva.model_copy(
        update={
            "state": IvaState.UNVERIFIED,
            "verification_code_hash": None,
            "verification_attempts": 0,
            "changed": changed,
        }
    )
    assert iva == expected_iva
    assert registry.published_events == [("iva_state_changed", iva)]


async def test_unverify_non_existing_iva():
    """Test trying to unverify a non-existing IVA."""
    registry = MockUserRegistry()
    random_iva_id = uuid4()
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"IVA with ID {random_iva_id} does not exist",
    ):
        await registry.unverify_iva(random_iva_id)
    assert not registry.published_events


async def test_request_iva_verification_code():
    """Test that a verification code for an IVA can be requested."""
    now = now_utc_ms_prec()
    before = now - timedelta(hours=3)
    registry = MockUserRegistry()
    registry.add_dummy_iva(state=IvaState.UNVERIFIED, created=before, changed=before)
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    from_iva = ivas[0]
    await registry.request_iva_verification_code(IVA_IDS[0], user_id=ID_OF_JOHN)
    assert len(ivas) == 1
    iva = ivas[0]
    changed = iva.changed
    assert 0 <= (changed - now).total_seconds() < 3
    expected_iva = from_iva.model_copy(
        update={
            "state": IvaState.CODE_REQUESTED,
            "changed": changed,
        }
    )
    assert iva == expected_iva
    assert registry.published_events == [("iva_state_changed", iva)]


async def test_request_verification_code_for_non_existing_iva():
    """Test requesting a verification code for a non-existing IVA."""
    registry = MockUserRegistry()
    random_iva_id = uuid4()
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"IVA with ID {random_iva_id} does not exist",
    ):
        await registry.request_iva_verification_code(random_iva_id)
    assert not registry.published_events


async def test_request_verification_code_for_different_user():
    """Test requesting a verification code for a different user."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(state=IvaState.UNVERIFIED)
    assert len(registry.dummy_ivas) == 1
    # first test with a different user ID
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"User with ID {ID_OF_JANE} does not have an IVA with ID {IVA_IDS[0]}",
    ):
        await registry.request_iva_verification_code(IVA_IDS[0], user_id=ID_OF_JANE)
    assert not registry.published_events
    # now test again with the right user ID
    await registry.request_iva_verification_code(IVA_IDS[0], user_id=ID_OF_JOHN)
    iva = registry.dummy_ivas[0]
    assert iva.state == IvaState.CODE_REQUESTED
    assert registry.published_events == [("iva_state_changed", iva)]


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.CODE_REQUESTED,
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
        IvaState.VERIFIED,
    ],
)
async def test_request_iva_verification_code_with_invalid_state(from_state: IvaState):
    """Test requesting a verification code for an IVA in an invalid state."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(state=from_state)
    with pytest.raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {IVA_IDS[0]} has an unexpected state {from_state.name}",
    ):
        await registry.request_iva_verification_code(IVA_IDS[0])
    assert not registry.published_events


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.CODE_REQUESTED,
        IvaState.CODE_CREATED,
    ],
)
async def test_create_iva_verification_code(from_state: IvaState):
    """Test the creation of an IVA verification code."""
    now = now_utc_ms_prec()
    before = now - timedelta(hours=3)
    registry = MockUserRegistry()
    registry.add_dummy_iva(state=from_state, created=before, changed=before)
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    from_iva = ivas[0]
    assert not from_iva.verification_code_hash
    code = await registry.create_iva_verification_code(IVA_IDS[0])
    assert len(ivas) == 1
    assert isinstance(code, str)
    assert code.isascii()
    assert code.isalnum()
    assert code.isupper()
    assert len(code) == VERIFICATION_CODE_SIZE
    iva = ivas[0]
    changed = iva.changed
    assert 0 <= (changed - now).total_seconds() < 3
    verification_code_hash = iva.verification_code_hash
    assert verification_code_hash
    assert validate_code(code, verification_code_hash)
    expected_iva = from_iva.model_copy(
        update={
            "state": IvaState.CODE_CREATED,
            "verification_code_hash": verification_code_hash,
            "changed": changed,
        }
    )
    assert iva == expected_iva
    assert not registry.published_events


async def test_create_verification_code_for_non_existing_iva():
    """Test creating a verification code for a non-existing IVA."""
    registry = MockUserRegistry()
    random_iva_id = uuid4()
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"IVA with ID {random_iva_id} does not exist",
    ):
        await registry.create_iva_verification_code(random_iva_id)


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.UNVERIFIED,
        IvaState.CODE_TRANSMITTED,
        IvaState.VERIFIED,
    ],
)
async def test_create_iva_verification_code_with_invalid_state(from_state: IvaState):
    """Test creating a verification code for an IVA in an invalid state."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(state=from_state)
    with pytest.raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {IVA_IDS[0]} has an unexpected state {from_state.name}",
    ):
        await registry.create_iva_verification_code(IVA_IDS[0])


async def test_confirm_iva_transmission():
    """Test confirming the transmission of an IVA verification code."""
    now = now_utc_ms_prec()
    before = now - timedelta(hours=3)
    registry = MockUserRegistry()
    registry.add_dummy_iva(state=IvaState.CODE_CREATED, created=before, changed=before)
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    from_iva = ivas[0]
    await registry.confirm_iva_code_transmission(IVA_IDS[0])
    assert len(ivas) == 1
    iva = ivas[0]
    changed = iva.changed
    assert 0 <= (changed - now).total_seconds() < 3
    expected_iva = from_iva.model_copy(
        update={
            "state": IvaState.CODE_TRANSMITTED,
            "changed": changed,
        }
    )
    assert iva == expected_iva
    assert registry.published_events


async def test_confirm_verification_code_transmission_for_non_existing_iva():
    """Test confirming transmission of a verification code for a non-existing IVA."""
    registry = MockUserRegistry()
    random_iva_id = uuid4()
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"IVA with ID {random_iva_id} does not exist",
    ):
        await registry.confirm_iva_code_transmission(random_iva_id)


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.VERIFIED,
        IvaState.CODE_REQUESTED,
        IvaState.CODE_TRANSMITTED,
        IvaState.VERIFIED,
    ],
)
async def test_confirm_code_transmission_with_invalid_state(from_state: IvaState):
    """Test confirming transmission of a code for an IVA in an invalid state."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(state=from_state)
    with pytest.raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {IVA_IDS[0]} has an unexpected state {from_state.name}",
    ):
        await registry.confirm_iva_code_transmission(IVA_IDS[0])


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
    ],
)
@pytest.mark.parametrize("attempts", [0, 1, 2, 5, 8, 9])
async def test_validate_iva_verification_code(from_state: IvaState, attempts: int):
    """Test validating a verification code for an IVA."""
    now = now_utc_ms_prec()
    before = now - timedelta(hours=3)
    registry = MockUserRegistry()
    code = generate_code()
    verification_code_hash = hash_code(code)
    registry.add_dummy_iva(
        state=from_state,
        verification_attempts=attempts,
        verification_code_hash=verification_code_hash,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    from_iva = ivas[0]
    validated = await registry.validate_iva_verification_code(
        IVA_IDS[0], code, user_id=ID_OF_JOHN
    )
    assert validated is True
    assert len(ivas) == 1
    iva = ivas[0]
    changed = iva.changed
    assert 0 <= (changed - now).total_seconds() < 3
    expected_iva = from_iva.model_copy(
        update={
            "state": IvaState.VERIFIED,
            "verification_attempts": 0,
            "verification_code_hash": None,
            "changed": changed,
        }
    )
    assert iva == expected_iva
    assert registry.published_events == [("iva_state_changed", iva)]


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
    ],
)
@pytest.mark.parametrize("attempts", [0, 1, 2, 5, 8, 9])
async def test_validate_iva_with_invalid_verification_code(
    from_state: IvaState, attempts: int
):
    """Test validating an IVA with an invalid verification code."""
    now = now_utc_ms_prec()
    before = now - timedelta(hours=3)
    registry = MockUserRegistry()
    code = generate_code()
    verification_code_hash = hash_code(code)
    registry.add_dummy_iva(
        state=from_state,
        verification_attempts=attempts,
        verification_code_hash=verification_code_hash,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    from_iva = ivas[0]
    invalid_code = code[:-1] + ("Y" if code[-1] == "X" else "X")
    validated = await registry.validate_iva_verification_code(
        IVA_IDS[0], invalid_code, user_id=ID_OF_JOHN
    )
    assert validated is False
    assert len(ivas) == 1
    iva = ivas[0]
    changed = iva.changed
    assert 0 <= (changed - now).total_seconds() < 3
    expected_iva = from_iva.model_copy(
        update={
            "state": from_state,
            "verification_attempts": attempts + 1,
            "changed": changed,
        }
    )
    assert iva == expected_iva
    assert not registry.published_events


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
    ],
)
@pytest.mark.parametrize("attempts", [10, 15, 99])
async def test_validate_iva_verification_code_too_often(
    from_state: IvaState, attempts: int
):
    """Test validating a verification code for an IVA too often."""
    now = now_utc_ms_prec()
    before = now - timedelta(hours=3)
    registry = MockUserRegistry()
    code = generate_code()
    verification_code_hash = hash_code(code)
    registry.add_dummy_iva(
        state=from_state,
        verification_attempts=attempts,
        verification_code_hash=verification_code_hash,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    from_iva = ivas[0]
    with pytest.raises(
        registry.IvaTooManyVerificationAttemptsError,
        match=f"Too many verification attempts for IVA with ID {IVA_IDS[0]}",
    ):
        await registry.validate_iva_verification_code(
            IVA_IDS[0], code, user_id=ID_OF_JOHN
        )
    assert len(ivas) == 1
    iva = ivas[0]
    changed = iva.changed
    assert 0 <= (changed - now).total_seconds() < 3
    expected_iva = from_iva.model_copy(
        update={
            "state": IvaState.UNVERIFIED,
            "verification_attempts": 0,
            "verification_code_hash": None,
            "changed": changed,
        }
    )
    assert iva == expected_iva
    assert registry.published_events == [("iva_state_changed", iva)]


async def test_validate_verification_code_for_non_existing_iva():
    """Test validating a verification code for a non-existing IVA."""
    registry = MockUserRegistry()
    random_iva_id = uuid4()
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"IVA with ID {random_iva_id} does not exist",
    ):
        await registry.validate_iva_verification_code(random_iva_id, "123456")
    assert not registry.published_events


async def test_validate_verification_code_for_different_user():
    """Test validating a verification code for a different user."""
    registry = MockUserRegistry()
    now = now_utc_ms_prec()
    before = now - timedelta(hours=3)
    registry = MockUserRegistry()
    code = generate_code()
    verification_code_hash = hash_code(code)
    registry.add_dummy_iva(
        state=IvaState.CODE_TRANSMITTED,
        verification_code_hash=verification_code_hash,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    with pytest.raises(
        registry.IvaDoesNotExistError,
        match=f"User with ID {ID_OF_JANE} does not have an IVA with ID {IVA_IDS[0]}",
    ):
        await registry.validate_iva_verification_code(
            IVA_IDS[0], code, user_id=ID_OF_JANE
        )
    assert not registry.published_events
    validated = await registry.validate_iva_verification_code(
        IVA_IDS[0], code, user_id=ID_OF_JOHN
    )
    assert validated is True
    assert ivas[0].state == IvaState.VERIFIED
    assert registry.published_events == [("iva_state_changed", ivas[0])]


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.UNVERIFIED,
        IvaState.CODE_REQUESTED,
        IvaState.VERIFIED,
    ],
)
async def test_validate_verification_code_with_invalid_state(from_state: IvaState):
    """Test validating a verification code for an IVA in an invalid state."""
    registry = MockUserRegistry()
    code = generate_code()
    verification_code_hash = hash_code(code)
    registry.add_dummy_iva(
        state=from_state, verification_code_hash=verification_code_hash
    )
    with pytest.raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {IVA_IDS[0]} has an unexpected state {from_state.name}",
    ):
        await registry.validate_iva_verification_code(IVA_IDS[0], code)
    assert not registry.published_events


@pytest.mark.parametrize(
    "from_state",
    [
        IvaState.UNVERIFIED,
        IvaState.CODE_REQUESTED,
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
        IvaState.VERIFIED,
    ],
)
async def test_validate_verification_code_without_hash(from_state: IvaState):
    """Test validating a verification code for an IVA without hash of the code."""
    registry = MockUserRegistry()
    registry.add_dummy_iva(state=from_state)
    with pytest.raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {IVA_IDS[0]} has an unexpected state {from_state.name}",
    ):
        await registry.validate_iva_verification_code(IVA_IDS[0], "123456")
    assert not registry.published_events


async def test_reset_verified_ivas():
    """Test resetting all verified IVAs."""
    registry = MockUserRegistry()
    for user_id in (ID_OF_JOHN, ID_OF_JANE):
        for type_ in IvaType.PHONE, IvaType.FAX:
            for state in IvaState.__members__.values():
                registry.add_dummy_iva(state=state, type_=type_, user_id=user_id)
    dummy_ivas = registry.dummy_ivas
    old_ivas = list(dummy_ivas)
    await registry.reset_verified_ivas(ID_OF_JOHN)
    assert len(dummy_ivas) == len(old_ivas)
    for old_iva, new_iva in zip(old_ivas, dummy_ivas, strict=True):
        if old_iva.user_id == ID_OF_JOHN and old_iva.state == IvaState.VERIFIED:
            assert new_iva.state == IvaState.UNVERIFIED
            assert new_iva == old_iva.model_copy(
                update={"state": IvaState.UNVERIFIED, "changed": new_iva.changed}
            )
        else:
            assert old_iva is new_iva
    assert registry.published_events == [("ivas_reset", ID_OF_JOHN)]


async def test_iva_verification_happy_path():
    """Test happy path of a complete IVA verification."""
    registry = MockUserRegistry()
    iva_data = IvaBasicData(type=IvaType.PHONE, value="123456")
    user_id = ID_OF_JOHN
    iva_id = await registry.create_iva(user_id, iva_data)
    assert iva_id
    ivas = registry.dummy_ivas
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva.id == iva_id
    assert iva.state == IvaState.UNVERIFIED
    assert iva.verification_code_hash is None
    assert iva.verification_attempts == 0
    # request code
    await registry.request_iva_verification_code(iva_id, user_id=user_id)
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva.state == IvaState.CODE_REQUESTED
    assert iva.verification_code_hash is None
    assert iva.verification_attempts == 0
    assert registry.published_events == [("iva_state_changed", iva)]
    registry.published_events.clear()
    # create code
    code = await registry.create_iva_verification_code(iva_id)
    assert isinstance(code, str)
    assert code.isascii()
    assert code.isalnum()
    assert code.isupper()
    assert len(code) == VERIFICATION_CODE_SIZE
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva.state == IvaState.CODE_CREATED
    assert iva.verification_code_hash is not None
    assert iva.verification_attempts == 0
    assert not registry.published_events
    # transmit code
    await registry.confirm_iva_code_transmission(iva_id)
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva.state == IvaState.CODE_TRANSMITTED
    assert iva.verification_code_hash is not None
    assert iva.verification_attempts == 0
    assert registry.published_events == [("iva_state_changed", iva)]
    registry.published_events.clear()
    # validate code
    validated = await registry.validate_iva_verification_code(
        iva_id, code, user_id=user_id
    )
    assert len(ivas) == 1
    iva = ivas[0]
    assert validated is True
    assert iva.state == IvaState.VERIFIED
    assert iva.verification_code_hash is None
    assert iva.verification_attempts == 0
    assert registry.published_events == [("iva_state_changed", iva)]
