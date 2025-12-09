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

"""Test User and IVA models and show some usage examples."""

from uuid import UUID

import pytest
from hexkit.utils import now_utc_ms_prec
from pydantic import ValidationError

from auth_service.user_registry.models.ivas import Iva, IvaState, IvaType
from auth_service.user_registry.models.users import AcademicTitle, User, UserStatus

from ...fixtures.constants import EXT_ID_OF_JOHN, ID_OF_JOHN


def test_create_user() -> None:
    """Test creating a user."""
    now = now_utc_ms_prec()
    user = User(
        name="John Doe",
        title=AcademicTitle.DR,
        email="john.doe@home.org",
        status=UserStatus.ACTIVE,
        ext_id=EXT_ID_OF_JOHN,
        registration_date=now,
    )
    assert isinstance(user.id, UUID)


def test_create_iva() -> None:
    """Test creating an IVA."""
    now = now_utc_ms_prec()
    iva = Iva(
        user_id=ID_OF_JOHN,
        type=IvaType.POSTAL_ADDRESS,
        value="Sesame Street 1, 12345 Springfield",
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    assert isinstance(iva.id, UUID)


@pytest.mark.parametrize("iva_type", [IvaType.PHONE, IvaType.FAX])
def test_iva_with_valid_phone_number(iva_type) -> None:
    """Test creating an IVA with a valid phone number."""
    now = now_utc_ms_prec()
    iva = Iva(
        user_id=ID_OF_JOHN,
        type=iva_type,
        # phone number input is allowed to be not normalized
        value="+49 (0221) 4710 123",
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    assert isinstance(iva.id, UUID)
    # phone number should be normalized after validation
    assert iva.value == "+492214710123"


@pytest.mark.parametrize("iva_type", [IvaType.PHONE, IvaType.FAX])
@pytest.mark.parametrize(
    "number",
    [
        "foo bar",  # invalid format
        "(0221) 4710 123",  # missing country code
        "+99 12345678",  # invalid country code
        "+49 123456 7890",  # invalid area code
    ],
)
def test_iva_with_invalid_phone_number(iva_type: IvaType, number: str) -> None:
    """Test creating an IVA with an invalid phone number."""
    now = now_utc_ms_prec()
    with pytest.raises(ValidationError, match="Invalid phone number"):
        Iva(
            user_id=ID_OF_JOHN,
            type=iva_type,
            value=number,
            state=IvaState.VERIFIED,
            created=now,
            changed=now,
        )


@pytest.mark.parametrize("iva_type", [IvaType.IN_PERSON, IvaType.POSTAL_ADDRESS])
def test_iva_with_other_types(iva_type) -> None:
    """Test creating an IVA with other types."""
    now = now_utc_ms_prec()
    iva = Iva(
        user_id=ID_OF_JOHN,
        type=iva_type,
        value="foo bar",
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    assert isinstance(iva.id, UUID)
    assert iva.value == "foo bar"
