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

"""Unit tests for the core user and IVA registry."""

from datetime import timedelta
from typing import cast

from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest import mark, raises

from auth_service.config import CONFIG
from auth_service.user_management.user_registry.core.registry import (
    IvaDao,
    UserDao,
    UserRegistry,
)
from auth_service.user_management.user_registry.core.verification_codes import (
    generate_code,
    hash_code,
    validate_code,
)
from auth_service.user_management.user_registry.models.ivas import (
    Iva,
    IvaBasicData,
    IvaData,
    IvaState,
    IvaType,
)
from auth_service.user_management.user_registry.models.users import (
    AcademicTitle,
    User,
    UserBasicData,
    UserModifiableData,
    UserRegisteredData,
    UserStatus,
)

from ....fixtures.utils import DummyIvaDao, DummyUserDao

pytestmark = mark.asyncio()


VERIFICATION_CODE_SIZE = 6  # the expected size of verification codes


class UserRegistryForTesting(UserRegistry):
    """A modified user registry for testing."""

    def __init__(self):
        self.dummy_user_dao = DummyUserDao()
        self.dummy_iva_dao = DummyIvaDao()
        super().__init__(
            config=CONFIG,
            user_dao=cast(UserDao, self.dummy_user_dao),
            iva_dao=cast(IvaDao, self.dummy_iva_dao),
        )

    @staticmethod
    def is_internal_user_id(id_: str) -> bool:
        """Check if the passed ID is an internal user id."""
        return isinstance(id_, str) and id_.endswith("@ghga.de")

    @staticmethod
    def is_external_user_id(id_: str) -> bool:
        """Check if the passed ID is an external user id."""
        return isinstance(id_, str) and id_.endswith("@aai.org")

    @property
    def dummy_user(self) -> User:
        """Get the dummy user."""
        return self.dummy_user_dao.user

    @property
    def dummy_ivas(self) -> list[Iva]:
        """Get the dummy IVAs."""
        return self.dummy_iva_dao.ivas


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
    registry = UserRegistryForTesting()
    user = registry.dummy_user_dao.user
    user_data = UserRegisteredData(
        ext_id=user.ext_id, name="John Foo", email="foo@home.org"
    )
    with raises(
        UserRegistry.UserAlreadyExistsError,
        match=f"Could not create user with external ID {user.ext_id}:"
        " user already exists",
    ):
        await registry.create_user(user_data)


async def test_create_new_user():
    """Test creating a user account that does not yet exist."""
    registry = UserRegistryForTesting()
    user = registry.dummy_user
    user_data = UserRegisteredData(
        ext_id="jane@aai.org",
        name="John Roe",
        title=AcademicTitle.DR,
        email="jane@home.org",
    )
    user = await registry.create_user(user_data)
    assert user == registry.dummy_user
    assert user.id == "jane@ghga.de"
    assert registry.is_internal_user_id(user.id)
    assert user.ext_id == "jane@aai.org"
    assert user.status == UserStatus.ACTIVE
    assert 0 <= (now_as_utc() - user.registration_date).total_seconds() < 3


async def test_get_existing_user():
    """Test getting an existing user."""
    registry = UserRegistryForTesting()
    dummy_user = registry.dummy_user
    user = await registry.get_user(dummy_user.id)
    assert user is dummy_user


async def test_get_non_existing_user():
    """Test trying to get a non-existing user."""
    registry = UserRegistryForTesting()
    with raises(
        registry.UserDoesNotExistError, match="User with ID jane@ghga.de does not exist"
    ):
        await registry.get_user("jane@ghga.de")


async def test_update_basic_data():
    """Test updating the basic data of an existing user."""
    registry = UserRegistryForTesting()
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
    registry = UserRegistryForTesting()
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
    registry = UserRegistryForTesting()
    dummy_user = registry.dummy_user
    basic_data = UserModifiableData(status=UserStatus.INACTIVE)
    await registry.update_user(
        dummy_user.id,
        basic_data,
        changed_by="some-steward",
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
    assert status_change.by == "some-steward"
    assert status_change.context == "This is some context."
    change_date = status_change.change_date
    assert change_date
    assert 0 <= (now_as_utc() - change_date).total_seconds() < 3


async def test_update_modifiable_data_title_and_status():
    """Test updating the title and the status of an existing user."""
    registry = UserRegistryForTesting()
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
    assert 0 <= (now_as_utc() - change_date).total_seconds() < 3


async def test_update_non_existing_user():
    """Test updating the basic data of a non-existing user."""
    registry = UserRegistryForTesting()
    basic_data = UserBasicData(name="John Doe", email="john@home.org")
    with raises(
        registry.UserDoesNotExistError,
        match="User with ID nobody@ghga.de does not exist",
    ):
        await registry.update_user("nobody@ghga.de", basic_data)


async def test_delete_existing_user():
    """Test deleting an existing user."""
    registry = UserRegistryForTesting()
    await registry.delete_user("john@ghga.de")
    dummy_user = registry.dummy_user
    assert dummy_user.id == "deleted"


async def test_delete_non_existing_user():
    """Test deleting a non-existing user."""
    registry = UserRegistryForTesting()
    with raises(
        registry.UserDoesNotExistError,
        match="User with ID nobody@ghga.de does not exist",
    ):
        await registry.delete_user("nobody@ghga.de")


async def test_delete_existing_user_with_ivas():
    """Test deleting an existing user who has IVAs."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    dummy_ivas = registry.dummy_ivas
    dummy_ivas.extend(
        (
            Iva(
                id="iva-1",
                user_id="john@ghga.de",
                type=IvaType.PHONE,
                value="123",
                created=now,
                changed=now,
            ),
            Iva(
                id="iva-2",
                user_id="jane@ghga.de",
                type=IvaType.PHONE,
                value="456",
                created=now,
                changed=now,
            ),
            Iva(
                id="iva-3",
                user_id="john@ghga.de",
                type=IvaType.FAX,
                value="789",
                created=now,
                changed=now,
            ),
        )
    )
    assert len(dummy_ivas) == 3
    await registry.delete_user("john@ghga.de")
    dummy_user = registry.dummy_user
    assert dummy_user.id == "deleted"
    assert len(dummy_ivas) == 1
    assert dummy_ivas[0].user_id == "jane@ghga.de"


async def test_create_new_iva():
    """Test creating a new IVA."""
    registry = UserRegistryForTesting()
    iva_data = IvaBasicData(type=IvaType.PHONE, value="123456")
    iva_id = await registry.create_iva("john@ghga.de", iva_data)
    assert iva_id
    ivas = registry.dummy_ivas
    assert isinstance(ivas, list)
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva.id == iva_id
    assert iva.user_id == "john@ghga.de"
    assert iva.type == IvaType.PHONE
    assert iva.value == "123456"
    assert iva.state == IvaState.UNVERIFIED
    assert iva.verification_code_hash is None
    assert iva.verification_attempts == 0
    assert 0 <= (now_as_utc() - iva.created).total_seconds() < 3
    assert 0 <= (now_as_utc() - iva.changed).total_seconds() < 3


async def test_create_iva_for_non_existing_user():
    """Test creating an IVA for a non-existing user."""
    registry = UserRegistryForTesting()
    iva_data = IvaBasicData(type=IvaType.PHONE, value="123456")
    with raises(
        registry.UserDoesNotExistError,
        match="User with ID nobody@ghga.de does not exist",
    ):
        await registry.create_iva("nobody@ghga.de", iva_data)


async def test_get_ivas_of_non_existing_user():
    """Test trying to get all IVAs of a non-existing user."""
    registry = UserRegistryForTesting()
    ivas = await registry.get_ivas("nobody@ghga.de")
    assert isinstance(ivas, list)
    assert not ivas


async def test_get_ivas_of_an_existing_user_without_ivas():
    """Test getting all IVAs of an existing user without IVAS."""
    registry = UserRegistryForTesting()
    ivas = await registry.get_ivas("john@ghga.de")
    assert isinstance(ivas, list)
    assert not ivas


async def test_get_ivas_of_an_existing_user_with_ivas():
    """Test getting all IVAs of an existing user without IVAS."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    dummy_ivas = [
        Iva(
            id="iva-1",
            user_id="john@ghga.de",
            type=IvaType.PHONE,
            value="123",
            created=now,
            changed=now,
        ),
        Iva(
            id="iva-2",
            user_id="jane@ghga.de",
            type=IvaType.PHONE,
            value="456",
            created=now,
            changed=now,
        ),
        Iva(
            id="iva-3",
            user_id="john@ghga.de",
            type=IvaType.FAX,
            value="789",
            created=now,
            changed=now,
        ),
    ]
    assert not registry.dummy_ivas
    registry.dummy_ivas.extend(dummy_ivas)
    ivas = await registry.get_ivas("john@ghga.de")
    assert isinstance(ivas, list)
    assert len(ivas) == 2
    for iva in ivas:
        assert isinstance(iva, IvaData)
    assert [Iva(**iva.model_dump(), user_id="john@ghga.de") for iva in ivas] == [
        iva for iva in dummy_ivas if iva.user_id.startswith("john")
    ]


async def test_delete_existing_iva():
    """Test deleting an existing IVA."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    dummy_ivas = registry.dummy_ivas
    dummy_ivas.extend(
        (
            Iva(
                id="iva-1",
                user_id="john@ghga.de",
                type=IvaType.PHONE,
                value="123",
                created=now,
                changed=now,
            ),
            Iva(
                id="iva-2",
                user_id="jane@ghga.de",
                type=IvaType.PHONE,
                value="456",
                created=now,
                changed=now,
            ),
        )
    )
    assert len(dummy_ivas) == 2
    await registry.delete_iva("iva-2")
    assert len(dummy_ivas) == 1
    assert dummy_ivas[0].id == "iva-1"
    await registry.delete_iva("iva-1")
    assert not dummy_ivas


async def test_delete_non_existing_iva():
    """Test deleting a non-existing IVA."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    dummy_ivas = registry.dummy_ivas
    dummy_ivas.append(
        Iva(
            id="iva-1",
            user_id="john@ghga.de",
            type=IvaType.PHONE,
            value="123",
            created=now,
            changed=now,
        ),
    )
    assert len(dummy_ivas) == 1
    with raises(
        registry.IvaDoesNotExistError, match="IVA with ID iva-2 does not exist"
    ):
        await registry.delete_iva("iva-2")


async def test_delete_iva_for_a_user():
    """Test deleting an IVA for a given user."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    dummy_ivas = registry.dummy_ivas
    dummy_ivas.append(
        Iva(
            id="iva-1",
            user_id="john@ghga.de",
            type=IvaType.PHONE,
            value="123",
            created=now,
            changed=now,
        ),
    )
    assert len(dummy_ivas) == 1
    await registry.delete_iva("iva-1", user_id="john@ghga.de")
    assert not dummy_ivas


async def test_delete_iva_for_nonexisting_user():
    """Test deleting an IVA for a non-existing user."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    dummy_ivas = registry.dummy_ivas
    dummy_ivas.append(
        Iva(
            id="iva-1",
            user_id="john@ghga.de",
            type=IvaType.PHONE,
            value="123",
            created=now,
            changed=now,
        ),
    )
    assert len(dummy_ivas) == 1
    with raises(
        registry.IvaDoesNotExistError,
        match="User with ID nobody@ghga.de does not have an IVA with ID iva-1",
    ):
        await registry.delete_iva("iva-1", user_id="nobody@ghga.de")


async def test_delete_iva_for_wrong_user():
    """Test deleting an IVA for the wrong user."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    dummy_ivas = registry.dummy_ivas
    dummy_ivas.append(
        Iva(
            id="iva-1",
            user_id="john@ghga.de",
            type=IvaType.PHONE,
            value="123",
            created=now,
            changed=now,
        ),
    )
    assert len(dummy_ivas) == 1
    with raises(
        registry.IvaDoesNotExistError,
        match="User with ID jane@ghga.de does not have an IVA with ID iva-1",
    ):
        await registry.delete_iva("iva-1", user_id="jane@ghga.de")
    assert len(dummy_ivas) == 1
    assert dummy_ivas[0].id == "iva-1"


@mark.parametrize(
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
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    from_iva = Iva(
        id=iva_id,
        state=from_state,
        type=IvaType.PHONE,
        value="123456",
        user_id="some-user-id",
        verification_code_hash="some-hash",
        verification_attempts=3,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    await registry.unverify_iva(iva_id)
    assert len(ivas) == 1
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


async def test_unverify_non_existing_iva():
    """Test trying to unverify a non-existing IVA."""
    registry = UserRegistryForTesting()
    with raises(
        registry.IvaDoesNotExistError,
        match="IVA with ID non-existing-iva-id does not exist",
    ):
        await registry.unverify_iva("non-existing-iva-id")


async def test_request_iva_verification_code():
    """Test that a verification code for an IVA can be requested."""
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    user_id = "some-user-id"
    from_iva = Iva(
        id=iva_id,
        state=IvaState.UNVERIFIED,
        type=IvaType.PHONE,
        value="123456",
        user_id=user_id,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    await registry.request_iva_verification_code(iva_id, user_id=user_id)
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


async def test_request_verification_code_for_non_existing_iva():
    """Test requesting a verification code for a non-existing IVA."""
    registry = UserRegistryForTesting()
    with raises(
        registry.IvaDoesNotExistError,
        match="IVA with ID non-existing-iva-id does not exist",
    ):
        await registry.request_iva_verification_code("non-existing-iva-id")


async def test_request_verification_code_for_different_user():
    """Test requesting a verification code for a different user."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    from_iva = Iva(
        id="some-iva-id",
        state=IvaState.UNVERIFIED,
        type=IvaType.PHONE,
        value="123456",
        user_id="some-user-id",
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    with raises(
        registry.IvaDoesNotExistError,
        match="User with ID other-user-id does not have an IVA with ID some-iva-id",
    ):
        await registry.request_iva_verification_code(
            "some-iva-id", user_id="other-user-id"
        )
    await registry.request_iva_verification_code("some-iva-id", user_id="some-user-id")
    assert ivas[0].state == IvaState.CODE_REQUESTED


@mark.parametrize(
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
    now = now_as_utc()
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    registry.dummy_ivas.append(
        Iva(
            id=iva_id,
            state=from_state,
            type=IvaType.PHONE,
            value="123456",
            user_id="some-user-id",
            created=now,
            changed=now,
        )
    )
    with raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {iva_id} has an unexpected state {from_state.name}",
    ):
        await registry.request_iva_verification_code(iva_id)


@mark.parametrize(
    "from_state",
    [
        IvaState.CODE_REQUESTED,
        IvaState.CODE_CREATED,
    ],
)
async def test_create_iva_verification_code(from_state: IvaState):
    """Test the creation of an IVA verification code."""
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    from_iva = Iva(
        id=iva_id,
        state=from_state,
        type=IvaType.PHONE,
        value="123456",
        user_id="some-user-id",
        created=before,
        changed=before,
    )
    assert not from_iva.verification_code_hash
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    code = await registry.create_iva_verification_code(iva_id)
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


async def test_create_verification_code_for_non_existing_iva():
    """Test creating a verification code for a non-existing IVA."""
    registry = UserRegistryForTesting()
    with raises(
        registry.IvaDoesNotExistError,
        match="IVA with ID non-existing-iva-id does not exist",
    ):
        await registry.create_iva_verification_code("non-existing-iva-id")


@mark.parametrize(
    "from_state",
    [
        IvaState.UNVERIFIED,
        IvaState.CODE_TRANSMITTED,
        IvaState.VERIFIED,
    ],
)
async def test_create_iva_verification_code_with_invalid_state(from_state: IvaState):
    """Test creating a verification code for an IVA in an invalid state."""
    now = now_as_utc()
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    registry.dummy_ivas.append(
        Iva(
            id=iva_id,
            state=from_state,
            type=IvaType.PHONE,
            value="123456",
            user_id="some-user-id",
            created=now,
            changed=now,
        )
    )
    with raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {iva_id} has an unexpected state {from_state.name}",
    ):
        await registry.create_iva_verification_code(iva_id)


async def test_confirm_iva_transmission():
    """Test confirming the transmission of an IVA verification code."""
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    from_iva = Iva(
        id=iva_id,
        state=IvaState.CODE_CREATED,
        type=IvaType.PHONE,
        value="123456",
        user_id="some-user-id",
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    await registry.confirm_iva_code_transmission(iva_id)
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


async def test_confirm_verification_code_transmission_for_non_existing_iva():
    """Test confirming transmission of a verification code for a non-existing IVA."""
    registry = UserRegistryForTesting()
    with raises(
        registry.IvaDoesNotExistError,
        match="IVA with ID non-existing-iva-id does not exist",
    ):
        await registry.confirm_iva_code_transmission("non-existing-iva-id")


@mark.parametrize(
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
    now = now_as_utc()
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    registry.dummy_ivas.append(
        Iva(
            id=iva_id,
            state=from_state,
            type=IvaType.PHONE,
            value="123456",
            user_id="some-user-id",
            created=now,
            changed=now,
        )
    )
    with raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {iva_id} has an unexpected state {from_state.name}",
    ):
        await registry.confirm_iva_code_transmission(iva_id)


@mark.parametrize(
    "from_state",
    [
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
    ],
)
@mark.parametrize("attempts", [0, 1, 2, 5, 8, 9])
async def test_validate_iva_verification_code(from_state: IvaState, attempts: int):
    """Test validating a verification code for an IVA."""
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    user_id = "some-user-id"
    code = generate_code()
    verification_code_hash = hash_code(code)
    from_iva = Iva(
        id=iva_id,
        state=from_state,
        type=IvaType.PHONE,
        value="123456",
        user_id=user_id,
        verification_attempts=attempts,
        verification_code_hash=verification_code_hash,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    validated = await registry.validate_iva_verification_code(
        iva_id, code, user_id=user_id
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


@mark.parametrize(
    "from_state",
    [
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
    ],
)
@mark.parametrize("attempts", [0, 1, 2, 5, 8, 9])
async def test_validate_iva_with_invalid_verification_code(
    from_state: IvaState, attempts: int
):
    """Test validating an IVA with an invalid verification code."""
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    user_id = "some-user-id"
    code = generate_code()
    verification_code_hash = hash_code(code)
    from_iva = Iva(
        id=iva_id,
        state=from_state,
        type=IvaType.PHONE,
        value="123456",
        user_id=user_id,
        verification_attempts=attempts,
        verification_code_hash=verification_code_hash,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    invalid_code = code[:-1] + ("Y" if code[-1] == "X" else "X")
    validated = await registry.validate_iva_verification_code(
        iva_id, invalid_code, user_id=user_id
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


@mark.parametrize(
    "from_state",
    [
        IvaState.CODE_CREATED,
        IvaState.CODE_TRANSMITTED,
    ],
)
@mark.parametrize("attempts", [10, 15, 99])
async def test_validate_iva_verification_code_too_often(
    from_state: IvaState, attempts: int
):
    """Test validating a verification code for an IVA too often."""
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    user_id = "some-user-id"
    code = generate_code()
    verification_code_hash = hash_code(code)
    from_iva = Iva(
        id=iva_id,
        state=from_state,
        type=IvaType.PHONE,
        value="123456",
        user_id=user_id,
        verification_attempts=attempts,
        verification_code_hash=verification_code_hash,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    with raises(
        registry.IvaTooManyVerificationAttemptsError,
        match=f"Too many verification attempts for IVA with ID {iva_id}",
    ):
        await registry.validate_iva_verification_code(iva_id, code, user_id=user_id)
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


async def test_validate_verification_code_for_non_existing_iva():
    """Test validating a verification code for a non-existing IVA."""
    registry = UserRegistryForTesting()
    with raises(
        registry.IvaDoesNotExistError,
        match="IVA with ID non-existing-iva-id does not exist",
    ):
        await registry.validate_iva_verification_code("non-existing-iva-id", "123456")


async def test_validate_verification_code_for_different_user():
    """Test validating a verification code for a different user."""
    registry = UserRegistryForTesting()
    now = now_as_utc()
    before = now - timedelta(hours=3)
    registry = UserRegistryForTesting()
    code = generate_code()
    verification_code_hash = hash_code(code)
    from_iva = Iva(
        id="some-iva-id",
        state=IvaState.CODE_TRANSMITTED,
        type=IvaType.PHONE,
        value="123456",
        user_id="some-user-id",
        verification_code_hash=verification_code_hash,
        created=before,
        changed=before,
    )
    ivas = registry.dummy_ivas
    ivas.append(from_iva)
    with raises(
        registry.IvaDoesNotExistError,
        match="User with ID other-user-id does not have an IVA with ID some-iva-id",
    ):
        await registry.validate_iva_verification_code(
            "some-iva-id", code, user_id="other-user-id"
        )
    validated = await registry.validate_iva_verification_code(
        "some-iva-id", code, user_id="some-user-id"
    )
    assert validated is True
    assert ivas[0].state == IvaState.VERIFIED


@mark.parametrize(
    "from_state",
    [
        IvaState.UNVERIFIED,
        IvaState.CODE_REQUESTED,
        IvaState.VERIFIED,
    ],
)
async def test_validate_verification_code_with_invalid_state(from_state: IvaState):
    """Test validating a verification code for an IVA in an invalid state."""
    now = now_as_utc()
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    code = generate_code()
    verification_code_hash = hash_code(code)
    registry.dummy_ivas.append(
        Iva(
            id=iva_id,
            state=from_state,
            type=IvaType.PHONE,
            value="123456",
            user_id="some-user-id",
            verification_code_hash=verification_code_hash,
            created=now,
            changed=now,
        )
    )
    with raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {iva_id} has an unexpected state {from_state.name}",
    ):
        await registry.validate_iva_verification_code(iva_id, code)


@mark.parametrize(
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
    now = now_as_utc()
    registry = UserRegistryForTesting()
    iva_id = "some-iva-id"
    registry.dummy_ivas.append(
        Iva(
            id=iva_id,
            state=from_state,
            type=IvaType.PHONE,
            value="123456",
            user_id="some-user-id",
            verification_code_hash=None,
            created=now,
            changed=now,
        )
    )
    with raises(
        registry.IvaUnexpectedStateError,
        match=f"IVA with ID {iva_id} has an unexpected state {from_state.name}",
    ):
        await registry.validate_iva_verification_code(iva_id, "123456")


async def test_iva_verification_happy_path():
    """Test happy path of a complete IVA verification."""
    registry = UserRegistryForTesting()
    iva_data = IvaBasicData(type=IvaType.PHONE, value="123456")
    user_id = "john@ghga.de"
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
    # transmit code
    await registry.confirm_iva_code_transmission(iva_id)
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva.state == IvaState.CODE_TRANSMITTED
    assert iva.verification_code_hash is not None
    assert iva.verification_attempts == 0
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
