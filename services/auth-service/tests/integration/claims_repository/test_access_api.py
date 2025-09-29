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

"""Test the access grant REST API"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import status
from hexkit.utils import now_utc_ms_prec

from auth_service.claims_repository.deps import get_claim_dao
from auth_service.user_registry.deps import get_iva_dao, get_user_dao
from auth_service.user_registry.models.ivas import (
    Iva,
    IvaState,
    IvaType,
)
from auth_service.user_registry.models.users import UserStatus
from tests.fixtures.constants import (
    DATA_ACCESS_CLAIM_ID,
    DATA_ACCESS_IVA_ID,
    DATA_STEWARD_CLAIM_ID,
    ID_OF_JANE,
    ID_OF_JOHN,
    SOME_IVA_ID,
    SOME_USER_ID,
)

from ...fixtures.utils import MockClaimDao, MockIvaDao, MockUserDao
from .fixtures import FullClient, fixture_full_client  # noqa: F401
from .test_claims_api import DATASET_CLAIM_DATA

pytestmark = pytest.mark.asyncio()


async def test_grant_download_access(full_client: FullClient):
    """Test that granting access to a dataset works."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_utc_ms_prec()
    iva = Iva(
        id=SOME_IVA_ID,
        user_id=ID_OF_JOHN,
        value="(0123)456789",
        type=IvaType.PHONE,
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    iva_dao = MockIvaDao([iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    validity = {
        "valid_from": f"{now.year - 1}-01-01T00:00:00Z",
        "valid_until": f"{now.year + 1}-12-31T23:59:59Z",
    }

    # try to grant access using an invalid dataset accession
    response = await full_client.post(
        f"/download-access/users/{ID_OF_JOHN}/ivas/{SOME_IVA_ID}/datasets/not-a-dataset-id",
        json=validity,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # now try again with a valid dataset accession
    response = await full_client.post(
        f"/download-access/users/{ID_OF_JOHN}/ivas/{SOME_IVA_ID}/datasets/DS0815",
        json=validity,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = await full_client.get(f"/users/{ID_OF_JOHN}/claims")
    assert response.status_code == status.HTTP_200_OK
    requested_claims = response.json()

    assert len(requested_claims) == 1

    claim_data = requested_claims[0]
    assert claim_data.pop("id")
    creation_date = claim_data.pop("creation_date")
    assert creation_date
    assert claim_data.pop("assertion_date") == creation_date
    creation_datetime = datetime.fromisoformat(creation_date.replace("Z", "+00:00"))
    assert 0 <= (creation_datetime - now).total_seconds() < 5

    assert claim_data == {
        "asserted_by": "dac",
        "conditions": None,
        "revocation_date": None,
        "source": DATASET_CLAIM_DATA["source"],
        "sub_source": None,
        "user_id": str(ID_OF_JOHN),
        "iva_id": str(SOME_IVA_ID),
        "valid_from": validity["valid_from"],
        "valid_until": validity["valid_until"],
        "visa_type": DATASET_CLAIM_DATA["visa_type"],
        "visa_value": DATASET_CLAIM_DATA["visa_value"],
    }

    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == validity["valid_until"]

    response = await full_client.get(f"/download-access/users/{ID_OF_JOHN}/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"DS0815": validity["valid_until"]}


async def test_grant_download_access_with_unverified_iva(full_client: FullClient):
    """Test granting access to a dataset when the IVA is not yet verified."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_utc_ms_prec()
    iva = Iva(
        id=SOME_IVA_ID,
        user_id=ID_OF_JOHN,
        value="(0123)456789",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    iva_dao = MockIvaDao([iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    validity = {
        "valid_from": f"{now.year - 1}-01-01T00:00:00Z",
        "valid_until": f"{now.year + 1}-12-31T23:59:59Z",
    }

    response = await full_client.post(
        f"/download-access/users/{ID_OF_JOHN}/ivas/{SOME_IVA_ID}/datasets/DS0815",
        json=validity,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = await full_client.get(f"/users/{ID_OF_JOHN}/claims")
    assert response.status_code == status.HTTP_200_OK
    requested_claims = response.json()

    assert len(requested_claims) == 1
    claim_data = requested_claims[0]
    assert claim_data["user_id"] == str(ID_OF_JOHN)
    assert claim_data["iva_id"] == str(SOME_IVA_ID)

    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None

    response = await full_client.get(f"/download-access/users/{ID_OF_JOHN}/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


async def test_grant_download_access_without_iva(full_client: FullClient):
    """Test granting access to a dataset when the IVA does not exist."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = MockIvaDao()
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    year = now_utc_ms_prec().year
    validity = {
        "valid_from": f"{year - 1}-01-01T00:00:00Z",
        "valid_until": f"{year + 1}-12-31T23:59:59Z",
    }

    response = await full_client.post(
        f"/download-access/users/{ID_OF_JOHN}/ivas/{SOME_IVA_ID}/datasets/DS0815",
        json=validity,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The IVA was not found."

    response = await full_client.get(f"/users/{ID_OF_JOHN}/claims")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None

    response = await full_client.get(f"/download-access/users/{ID_OF_JOHN}/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}


async def test_check_download_access(full_client: FullClient):
    """Test that checking download access for a single dataset works."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_utc_ms_prec()
    iva = Iva(
        id=SOME_IVA_ID,
        user_id=ID_OF_JOHN,
        value="(0123)456789",
        type=IvaType.PHONE,
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    iva_dao = MockIvaDao([iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # post valid access permission for SOME_IVA_ID and DS0815

    current_timestamp = int(now.timestamp())
    claim_data: dict[str, Any] = {
        **DATASET_CLAIM_DATA,
        "iva_id": str(SOME_IVA_ID),
        "valid_from": current_timestamp,
        "valid_until": current_timestamp + 60,  # 60 seconds
    }

    response = await full_client.post(f"/users/{ID_OF_JOHN}/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0815"
    assert claim["user_id"] == str(ID_OF_JOHN)

    # post another one with longer validity

    claim_data = {
        **claim_data,
        "valid_until": current_timestamp + 60 * 5,  # 5 minutes
    }

    response = await full_client.post(f"/users/{ID_OF_JOHN}/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0815"
    assert claim["user_id"] == str(ID_OF_JOHN)

    # post invalid access permission for DS0814

    claim_data["visa_value"] = claim_data["visa_value"].replace("0815", "0814")
    claim_data["valid_from"] = current_timestamp - 60
    claim_data["valid_until"] = current_timestamp - 30

    response = await full_client.post(f"/users/{ID_OF_JOHN}/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0814"
    assert claim["user_id"] == str(ID_OF_JOHN)

    # check access for wrong user

    response = await full_client.get(
        f"/download-access/users/{SOME_USER_ID}/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."

    # check access for right user

    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_200_OK
    valid_until = response.json()
    assert isinstance(valid_until, str)

    # check that we get the longer validity period
    assert (
        int(datetime.fromisoformat(valid_until.replace("Z", "+00:00")).timestamp())
        - current_timestamp
        == 5 * 60
    )

    # check access for invalid dataset accession

    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/not-a-dataset-id"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # check access when permission exists but is not valid any more

    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/DS0814"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None

    # check access when dataset and permission does not exist

    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/DS0816"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None

    # check that access is denied when user is not active

    user_dao.users[0] = user_dao.users[0].model_copy(
        update={"status": UserStatus.INACTIVE}
    )
    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


async def test_check_download_access_with_unverified_iva(full_client: FullClient):
    """Test checking download access for a single dataset with an unverified IVA."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_utc_ms_prec()
    iva = Iva(
        id=SOME_IVA_ID,
        user_id=ID_OF_JOHN,
        value="(0123)456789",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    iva_dao = MockIvaDao([iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # post valid access permission for SOME_IVA_ID and DS0815

    current_timestamp = int(now.timestamp())
    claim_data: dict[str, Any] = {
        **DATASET_CLAIM_DATA,
        "iva_id": str(SOME_IVA_ID),
        "valid_from": current_timestamp,
        "valid_until": current_timestamp + 60,
    }

    response = await full_client.post(f"/users/{ID_OF_JOHN}/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0815"
    assert claim["user_id"] == str(ID_OF_JOHN)

    # check that access is not given when the IVA is not verified

    response = await full_client.get(
        f"/download-access/users/{ID_OF_JOHN}/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is None


async def test_get_datasets_with_download_access(full_client: FullClient):
    """Test that getting all datasets with download access works."""
    user_dao = MockUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_utc_ms_prec()
    unverified_iva_id_str = "58885d5a-420a-4fd7-9815-3fe79840ca58"
    verified_iva_id_str = "37591856-82d3-4b91-bf1a-50681c8d9811"
    unverified_iva = Iva(
        id=UUID(unverified_iva_id_str),
        user_id=ID_OF_JOHN,
        value="(0123)456789",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    verified_iva = unverified_iva.model_copy(
        update={"id": UUID(verified_iva_id_str), "state": IvaState.VERIFIED}
    )
    iva_dao = MockIvaDao([unverified_iva, verified_iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # should not have downloadable datasets in the beginning

    response = await full_client.get(f"/download-access/users/{ID_OF_JOHN}/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {}

    # post valid access permission for DS0815

    current_timestamp = int(now.timestamp())
    some_claim_data: dict[str, Any] = {
        **DATASET_CLAIM_DATA,
        "iva_id": verified_iva_id_str,
        "valid_from": current_timestamp,
        "valid_until": current_timestamp + 60,  # 60 seconds
    }

    response = await full_client.post(
        f"/users/{ID_OF_JOHN}/claims", json=some_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == str(ID_OF_JOHN)
    assert claim["iva_id"] == verified_iva_id_str
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0815"

    # post another one with longer validity

    some_claim_data = {
        **some_claim_data,
        "valid_until": current_timestamp + 60 * 5,  # 5 minutes
    }

    response = await full_client.post(
        f"/users/{ID_OF_JOHN}/claims", json=some_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == str(ID_OF_JOHN)
    assert claim["iva_id"] == verified_iva_id_str
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0815"

    # post valid access permission for DS0816

    another_claim_data = {
        **some_claim_data,
        "visa_value": some_claim_data["visa_value"].replace("0815", "0816"),
    }
    response = await full_client.post(
        f"/users/{ID_OF_JOHN}/claims", json=another_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == str(ID_OF_JOHN)
    assert claim["iva_id"] == verified_iva_id_str
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0816"

    # post valid access permission with unverified IVA for DS0817

    yet_another_claim_data = {
        **some_claim_data,
        "iva_id": unverified_iva_id_str,
        "visa_value": some_claim_data["visa_value"].replace("0815", "0817"),
    }

    response = await full_client.post(
        f"/users/{ID_OF_JOHN}/claims", json=yet_another_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == str(ID_OF_JOHN)
    assert claim["iva_id"] == unverified_iva_id_str
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0817"

    # post valid access permission for different user for DS0818

    foreign_claim_data = {
        **some_claim_data,
        "visa_value": some_claim_data["visa_value"].replace("0815", "0818"),
    }
    # pretend for the next query that Jane exists
    users = user_dao.users
    users.append(users[0].model_copy(update={"id": ID_OF_JANE}))
    response = await full_client.post(
        f"/users/{ID_OF_JANE}/claims", json=foreign_claim_data
    )
    users.pop()

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == str(ID_OF_JANE)
    assert claim["iva_id"] == verified_iva_id_str
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0818"

    # post invalid access permission for DS0814

    former_claim_data = {
        **some_claim_data,
        "iva_id": unverified_iva_id_str,
        "valid_from": current_timestamp - 60,
        "valid_until": current_timestamp - 30,
        "visa_value": some_claim_data["visa_value"].replace("0815", "0814"),
    }

    response = await full_client.post(
        f"/users/{ID_OF_JOHN}/claims", json=former_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == str(ID_OF_JOHN)
    assert claim["iva_id"] == unverified_iva_id_str
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0814"

    # get list of all claims

    response = await full_client.get(f"/users/{ID_OF_JOHN}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 5
    dataset_ids = {claim["visa_value"].rsplit("/", 1)[-1] for claim in response.json()}
    assert dataset_ids == {
        "DS0814",
        "DS0815",  # has two claims with shorter and longer validity
        "DS0816",
        "DS0817",
    }

    # check access for wrong user
    response = await full_client.get(f"/download-access/users/{ID_OF_JANE}/datasets")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."

    # check access for right user
    response = await full_client.get(f"/download-access/users/{ID_OF_JOHN}/datasets")
    assert response.status_code == status.HTTP_200_OK
    dataset_id_to_end_date = response.json()

    assert isinstance(dataset_id_to_end_date, dict)
    assert sorted(dataset_id_to_end_date) == ["DS0815", "DS0816"]

    valid_until = dataset_id_to_end_date["DS0815"]
    assert isinstance(valid_until, str)
    # check that we get the longer validity period
    assert (
        int(datetime.fromisoformat(valid_until.replace("Z", "+00:00")).timestamp())
        - current_timestamp
        == 5 * 60
    )  # 5 minutes

    # check that access is denied when user is not active
    user_dao.users[0] = user_dao.users[0].model_copy(
        update={"status": UserStatus.INACTIVE}
    )
    response = await full_client.get(f"/download-access/users/{ID_OF_JOHN}/datasets")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


async def test_fetch_access_grants(full_client: FullClient):
    """Test that access grants can be fetched and filters can be used."""
    user_dao = MockUserDao(title="Prof.", name="John Doe Sr.")
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    claim_dao = MockClaimDao()
    full_client.app.dependency_overrides[get_claim_dao] = lambda: claim_dao
    user = user_dao.users[0]
    assert user.name == "John Doe Sr."
    claim = claim_dao.claims[1]
    assert claim.visa_type == "ControlledAccessGrants"
    assert claim.user_id == user.id
    dt_to_str = lambda dt: dt.isoformat().replace("+00:00", "Z")

    expected_grants = [
        {
            "created": dt_to_str(claim.creation_date),
            "dataset_id": "DS0815",
            "id": str(DATA_ACCESS_CLAIM_ID),
            "iva_id": str(DATA_ACCESS_IVA_ID),
            "user_email": "john@home.org",
            "user_id": str(ID_OF_JOHN),
            "user_name": "John Doe Sr.",
            "user_title": "Prof.",
            "valid_from": dt_to_str(claim.valid_from),
            "valid_until": dt_to_str(claim.valid_until),
        },
    ]

    response = await full_client.get("/download-access/grants")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_grants

    # check filtering for the user ID
    response = await full_client.get(f"/download-access/grants?user_id={SOME_USER_ID}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    response = await full_client.get("/download-access/grants?user_id=invalid-id")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "should be a valid UUID" in response.json()["detail"][0]["msg"]
    response = await full_client.get(f"/download-access/grants?user_id={ID_OF_JOHN}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_grants

    # check filtering for the IVA ID
    response = await full_client.get(
        "/download-access/grants?iva_id=e04c283d-c16d-475b-85d7-748c9c701aeb"  # random
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    response = await full_client.get(
        f"/download-access/grants?iva_id={DATA_ACCESS_IVA_ID}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_grants

    # check filtering for the dataset ID
    response = await full_client.get("/download-access/grants?dataset_id=DS0917")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    response = await full_client.get(
        "/download-access/grants?dataset_id=invalid-accession"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    response = await full_client.get("/download-access/grants?dataset_id=DS0815")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_grants

    # check filtering for the validity
    response = await full_client.get("/download-access/grants?valid=false")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    response = await full_client.get("/download-access/grants?valid=true")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_grants


async def test_delete_access_grants(full_client: FullClient):
    """Test that access grants can be revoked."""
    claim_dao = MockClaimDao()
    full_client.app.dependency_overrides[get_claim_dao] = lambda: claim_dao
    claim = claim_dao.claims[1]
    assert claim.visa_type == "ControlledAccessGrants"
    claim_id = claim.id
    assert claim_id == DATA_ACCESS_CLAIM_ID
    num_claims = len(claim_dao.claims)

    assert await claim_dao.get_by_id(claim_id) is claim

    expected_error_status = status.HTTP_404_NOT_FOUND
    expected_error_detail = "The download access grant was not found."

    # try to revoke a claim that does not correspond to an access grant
    response = await full_client.delete(
        f"/download-access/grants/{DATA_STEWARD_CLAIM_ID}"
    )
    assert response.status_code == expected_error_status
    assert response.json()["detail"] == expected_error_detail

    # try to revoke a non-existing claim
    response = await full_client.delete(f"/download-access/grants/{uuid4()}")
    assert response.status_code == expected_error_status
    assert response.json()["detail"] == expected_error_detail

    # make sure that nothing has been changed
    assert len(claim_dao.claims) == num_claims
    assert await claim_dao.get_by_id(claim_id) is claim

    # revoke the existing access grant
    response = await full_client.delete(f"/download-access/grants/{claim_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # make sure the claim has actually been revoked, but not deleted
    assert len(claim_dao.claims) == num_claims
    updated_claim = await claim_dao.get_by_id(claim_id)
    assert updated_claim.revocation_date is not None
    assert 0 <= (now_utc_ms_prec() - updated_claim.revocation_date).total_seconds() < 3
    assert updated_claim.model_copy(update={"revocation_date": None}) == claim

    # try to revoke the access grant again
    response = await full_client.delete(f"/download-access/grants/{claim_id}")
    assert response.status_code == expected_error_status
    assert response.json()["detail"] == expected_error_detail

    # make sure that nothing has been changed
    assert len(claim_dao.claims) == num_claims
    assert await claim_dao.get_by_id(claim_id) is updated_claim
