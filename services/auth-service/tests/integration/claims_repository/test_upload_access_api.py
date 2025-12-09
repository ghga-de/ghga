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

"""Test upload access API functionality"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import status
from hexkit.utils import now_utc_ms_prec

from auth_service.claims_repository.deps import get_claim_dao
from auth_service.claims_repository.models.claims import VisaType
from auth_service.user_registry.deps import get_iva_dao, get_user_dao
from auth_service.user_registry.models.ivas import Iva, IvaState, IvaType
from tests.fixtures.constants import ID_OF_JOHN, PHONE_OF_JOHN

from ...fixtures.utils import MockClaimDao, MockIvaDao, MockUserDao
from .fixtures import FullClient, fixture_full_client  # noqa: F401

pytestmark = pytest.mark.asyncio()

now = now_utc_ms_prec()

UNVERIFIED_IVA_ID = uuid4()
UNVERIFIED_IVA = Iva(
    id=UNVERIFIED_IVA_ID,
    user_id=ID_OF_JOHN,
    value=PHONE_OF_JOHN,
    type=IvaType.PHONE,
    state=IvaState.UNVERIFIED,
    created=now,
    changed=now,
)

VERIFIED_IVA_ID = uuid4()
VERIFIED_IVA = Iva(
    id=VERIFIED_IVA_ID,
    user_id=ID_OF_JOHN,
    value=PHONE_OF_JOHN,
    type=IvaType.PHONE,
    state=IvaState.VERIFIED,
    created=now,
    changed=now,
)

# Test data for upload box claims
TEST_BOX_ID = UUID("cfeac7d0-bc58-4d00-975d-850c190c10a1")
UPLOAD_BOX_CLAIM_DATA = {
    "visa_type": "https://www.ghga.de/GA4GH/VisaTypes/Upload/v1.0",
    "visa_value": f"https://ghga.de/uploads/{TEST_BOX_ID}",
    "source": "https://ghga.de",
    "assertion_date": now.isoformat(),
    "asserted_by": "system",
}


def get_validity() -> dict[str, Any]:
    """Generate a validity dict based on current time"""
    return {
        "valid_from": now.isoformat(),
        "valid_until": (now + timedelta(weeks=52)).isoformat(),
    }


VALIDITY: dict[str, Any] = get_validity()
URL_JOHN = f"/upload-access/users/{ID_OF_JOHN}"


@pytest.mark.parametrize(
    "http_method, url",
    [
        (
            "post",
            f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/box123",
        ),
        ("post", f"{URL_JOHN}/ivas/iva123/boxes/{TEST_BOX_ID}"),
        (
            "post",
            f"/upload-access/users/user123/ivas/{VERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}",
        ),
        ("delete", "/upload-access/grants/grant123"),
        ("get", f"{URL_JOHN}/boxes/box123"),
        ("get", f"/upload-access/users/user123/boxes/{TEST_BOX_ID}"),
        ("get", "/upload-access/users/user123/boxes"),
    ],
    ids=[
        "GrantAccessBadBoxId",
        "GrantAccessBadIvaId",
        "GrantAccessBadUserId",
        "RevokeAccessBadGrantId",
        "CheckAccessBadBoxId",
        "CheckAccessBadUserId",
        "GetBoxesForUserBadUserId",
    ],
)
async def test_invalid_params_for_upload_access_endpoints(
    http_method: str, url: str, full_client: FullClient
):
    """Test calling various upload access endpoints with invalid path parameters"""
    response = await full_client.request(http_method, url, json=VALIDITY)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_grant_upload_access(full_client: FullClient):
    """Test granting upload access to a box."""
    claim_dao = MockClaimDao()
    full_client.app.dependency_overrides[get_claim_dao] = lambda: claim_dao
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao([VERIFIED_IVA])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    box_id = uuid4()
    validity = get_validity()
    response = await full_client.post(
        f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/{box_id}",
        json=validity,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Check that the claim was created, but check directly with a DAO
    claim = await claim_dao.find_one(mapping={"visa_type": VisaType.GHGA_UPLOAD})
    assert str(claim.visa_value).endswith(str(box_id))


async def test_check_upload_access(full_client: FullClient):
    """Test checking upload access for a single box."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao([VERIFIED_IVA])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # First grant upload access
    url = f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}"
    response = await full_client.post(url, json=VALIDITY)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Now check upload access
    url = f"{URL_JOHN}/boxes/{TEST_BOX_ID}"
    response = await full_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is not None
    assert (  # Account for format difference
        datetime.fromisoformat(response.json()).isoformat() == VALIDITY["valid_until"]
    )

    # Check access for non-existent box
    response = await full_client.get(f"{URL_JOHN}/boxes/{uuid4()}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None


async def test_get_boxes_with_upload_access(full_client: FullClient):
    """Test getting all boxes with upload access for a user."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao([VERIFIED_IVA])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # Grant upload access to multiple boxes
    box1 = str(uuid4())
    box2 = str(uuid4())
    for box_id in [box1, box2]:
        url = f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/{box_id}"
        response = await full_client.post(url, json=VALIDITY)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    # Get list of accessible boxes
    response = await full_client.get(f"{URL_JOHN}/boxes")
    assert response.status_code == status.HTTP_200_OK
    boxes = response.json()
    for k, v in boxes.items():
        boxes[k] = v.replace("Z", "+00:00")
    assert boxes == dict.fromkeys((box1, box2), VALIDITY["valid_until"])


async def test_get_upload_access_grants(full_client: FullClient):
    """Test getting upload access grants."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao([VERIFIED_IVA])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # Create an upload access claim
    url = f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}"
    response = await full_client.post(url, json=VALIDITY)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Get upload access grants
    response = await full_client.get("/upload-access/grants")
    assert response.status_code == status.HTTP_200_OK
    grants = response.json()
    assert isinstance(grants, list)
    assert len(grants) >= 1

    grant = grants[0]
    assert grant["user_id"] == str(ID_OF_JOHN)
    assert grant["iva_id"] == str(VERIFIED_IVA_ID)
    assert grant["box_id"] == str(TEST_BOX_ID)
    assert "user_name" in grant
    assert "user_email" in grant


async def test_grant_upload_access_with_unverified_iva(full_client: FullClient):
    """Test granting upload access to a box when the IVA is not yet verified."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao([UNVERIFIED_IVA])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # Grant access with an unverified IVA
    response = await full_client.post(
        f"{URL_JOHN}/ivas/{UNVERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}",
        json=VALIDITY,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Retrieve the test user's claims, which should have the one we just added
    response = await full_client.get(f"/users/{ID_OF_JOHN}/claims")
    assert response.status_code == status.HTTP_200_OK
    requested_claims = response.json()

    assert len(requested_claims) == 1
    claim_data = requested_claims[0]
    assert claim_data["user_id"] == str(ID_OF_JOHN)
    assert claim_data["iva_id"] == str(UNVERIFIED_IVA_ID)

    # Check if the user has access to the test box -- they shouldn't
    response = await full_client.get(f"{URL_JOHN}/boxes/{TEST_BOX_ID}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None

    response = await full_client.get(f"{URL_JOHN}/boxes")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


async def test_grant_upload_access_without_iva(full_client: FullClient):
    """Test granting upload access to a box when the IVA does not exist."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao()
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    response = await full_client.post(
        f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}",
        json=VALIDITY,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The IVA was not found."

    response = await full_client.get(f"/users/{ID_OF_JOHN}/claims")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    response = await full_client.get(f"{URL_JOHN}/boxes/{TEST_BOX_ID}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None

    response = await full_client.get(f"{URL_JOHN}/boxes")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


async def test_check_upload_access_with_unverified_iva(full_client: FullClient):
    """Test checking upload access for a single box with an unverified IVA."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao([UNVERIFIED_IVA])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # post valid upload access permission for UNVERIFIED_IVA_ID and TEST_BOX_ID
    url = f"{URL_JOHN}/ivas/{UNVERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}"
    response = await full_client.post(url, json=VALIDITY)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # check that access is not given when the IVA is not verified
    response = await full_client.get(f"{URL_JOHN}/boxes/{TEST_BOX_ID}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None


async def test_revoke_grant(full_client: FullClient):
    """Test revoking an upload access grant.

    This test also checks behavior for revoking an already-revoked grant, because
    the test setup is identical.
    """
    claim_dao = MockClaimDao()
    full_client.app.dependency_overrides[get_claim_dao] = lambda: claim_dao
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao([VERIFIED_IVA])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    url = f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}"
    response = await full_client.post(url, json=VALIDITY)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify that the claim was added by looking for a claim with matching details
    claim = await claim_dao.find_one(mapping={"visa_type": VisaType.GHGA_UPLOAD})
    assert str(claim.visa_value).endswith(str(TEST_BOX_ID))
    assert not claim.revocation_date

    # Now try to revoke the claim
    url = f"/upload-access/grants/{claim.id}"
    response = await full_client.delete(url)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Make sure the claim was revoked
    claim = await claim_dao.find_one(mapping={"visa_type": VisaType.GHGA_UPLOAD})

    assert str(claim.visa_value).endswith(str(TEST_BOX_ID))
    assert claim.revocation_date
    assert now_utc_ms_prec() - claim.revocation_date < timedelta(seconds=5)

    # Now revoke the grant again and make sure the endpoint returns a 404
    response = await full_client.delete(f"/upload-access/grants/{claim.id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # And ensure that the claim is not returned when queried
    url = f"{URL_JOHN}/boxes/{TEST_BOX_ID}"
    response = await full_client.get(url)
    assert response.json() is None


async def test_revoke_non_existent_grant(full_client: FullClient):
    """Test revoking an upload access grant -- should result in a 404."""
    response = await full_client.delete(f"/upload-access/grants/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_grant_access_for_invalid_dates(full_client: FullClient):
    """Test granting upload access for invalid dates"""
    url = f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}"
    validity = {
        "valid_from": now.isoformat(),
        "valid_until": (now - timedelta(hours=1)).isoformat(),
    }
    response = await full_client.post(url, json=validity)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    "valid_from, valid_until",
    [
        (now + timedelta(weeks=4), now + timedelta(weeks=52)),
        (now - timedelta(weeks=52), now - timedelta(weeks=4)),
    ],
    ids=["NotYetStarted", "AlreadyExpired"],
)
async def test_with_past_or_future_validity(
    valid_from: datetime, valid_until: datetime, full_client: FullClient
):
    """Test query endpoints when access hasn't begun yet."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao([VERIFIED_IVA])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # Create a validity period that starts in the future
    validity = {
        "valid_from": valid_from.isoformat(),
        "valid_until": valid_until.isoformat(),
    }

    # Grant access using that validity period
    url = f"{URL_JOHN}/ivas/{VERIFIED_IVA_ID}/boxes/{TEST_BOX_ID}"
    response = await full_client.post(url, json=validity)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Check boxes with upload access for the user - should be empty
    response = await full_client.get(f"{URL_JOHN}/boxes")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    # Check if the user has access to this box specifically
    response = await full_client.get(f"{URL_JOHN}/boxes/{TEST_BOX_ID}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None

    # Retrieve all valid upload grants and verify that this grant is absent
    response = await full_client.get("/upload-access/grants?valid=1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
