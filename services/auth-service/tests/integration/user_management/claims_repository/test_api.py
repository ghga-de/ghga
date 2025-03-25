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

"""Test the REST API"""

from datetime import datetime
from operator import itemgetter
from typing import Any

import pytest
from fastapi import status
from ghga_service_commons.utils.utc_dates import now_as_utc

from auth_service.user_management.user_registry.deps import get_iva_dao, get_user_dao
from auth_service.user_management.user_registry.models.ivas import (
    Iva,
    IvaState,
    IvaType,
)
from auth_service.user_management.user_registry.models.users import UserStatus

from ....fixtures.utils import DummyIvaDao, DummyUserDao
from .fixtures import FullClient, fixture_full_client  # noqa: F401

pytestmark = pytest.mark.asyncio()

ROLE_CLAIM_DATA = {
    "visa_type": "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0",
    "visa_value": "data_steward@ghga.de",
    "valid_from": "2022-10-01T12:00:00Z",
    "valid_until": "2022-10-31T12:00:00Z",
    "assertion_date": "2022-09-01T12:00:00Z",
    "source": "https://ghga.de",
    "asserted_by": "system",
}

DATASET_CLAIM_DATA = {
    "visa_type": "ControlledAccessGrants",
    "visa_value": "https://ghga.de/datasets/DS0815",
    "assertion_date": "2022-06-01T12:00:00Z",
    "source": "https://ghga.de",
    "asserted_by": "system",
}


async def test_health_check(full_client: FullClient):
    """Test that the health check endpoint works."""
    response = await full_client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


async def test_get_from_a_random_path(full_client: FullClient):
    """Test that a GET request to a random path raises a not found error."""
    response = await full_client.post("/some/random/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_post_claim(full_client: FullClient):
    """Test that creating a user claim works."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao

    response = await full_client.post(
        "/users/john@ghga.de/claims", json=ROLE_CLAIM_DATA
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED, claim

    claim_id = claim.pop("id", None)
    assert claim_id is not None
    assert len(claim_id) == 36
    assert claim_id.count("-") == 4
    assert claim.pop("user_id") == "john@ghga.de"
    assert claim.pop("iva_id") is None
    assert claim.pop("sub_source") is None

    assert claim.pop("conditions") is None
    assert claim.pop("revocation_date") is None
    assert claim.pop("creation_date") is not None

    assert claim == ROLE_CLAIM_DATA

    # test with non-existing user
    response = await full_client.post(
        "/users/john@haag.de/claims", json=ROLE_CLAIM_DATA
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


async def test_get_claims(full_client: FullClient):
    """Test that getting all claims of a user works."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao

    user_id = "john@ghga.de"

    # post two different claims
    claim1 = ROLE_CLAIM_DATA
    claim2 = {
        **claim1,
        "assertion_date": "2022-09-01T13:00:00Z",
        "visa_type": "ResearcherStatus",
        "visa_value": "researcher@ghga.de",
    }
    posted_claims = []
    for claim in (claim1, claim2):
        response = await full_client.post(f"/users/{user_id}/claims", json=claim)
        assert response.status_code == status.HTTP_201_CREATED
        posted_claims.append(response.json())

    response = await full_client.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    requested_claims = response.json()
    requested_claims.sort(key=itemgetter("assertion_date"))

    assert requested_claims == posted_claims

    assert requested_claims[0]["user_id"] == user_id
    assert requested_claims[1]["user_id"] == user_id
    assert requested_claims[0]["visa_type"] == ROLE_CLAIM_DATA["visa_type"]
    assert requested_claims[1]["visa_type"] == "ResearcherStatus"
    assert requested_claims[0]["visa_value"] != requested_claims[1]["visa_value"]

    # test with non-existing user
    response = await full_client.get("/users/john@haag.de/claims")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


async def test_patch_claim(full_client: FullClient):
    """Test that revoking a user claim works."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao

    user_id = "john@ghga.de"

    # post test claim
    response = await full_client.post(f"/users/{user_id}/claims", json=ROLE_CLAIM_DATA)
    posted_claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    claim_id = posted_claim["id"]
    assert claim_id is not None
    assert posted_claim.pop("revocation_date") is None

    # revoke test claim
    revocation_date = "2022-10-15T12:00:00Z"
    patch_data = {"revocation_date": revocation_date}
    response = await full_client.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # test that claim has been revoked
    response = await full_client.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]
    assert claim.pop("revocation_date") == revocation_date
    assert claim == posted_claim

    # test without revocation date
    patch_data = {"revocation_date": None}  # type: ignore
    response = await full_client.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # test with later revocation date
    patch_data = {"revocation_date": "2022-10-15T13:00:00Z"}
    response = await full_client.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "Already revoked earlier."

    # test with earlier revocation date
    revocation_date = "2022-10-15T11:00:00Z"
    patch_data = {"revocation_date": revocation_date}
    response = await full_client.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # test that revocation was advanced
    response = await full_client.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]
    assert claim.pop("revocation_date") == revocation_date
    assert claim == posted_claim

    # test with non-existing user
    response = await full_client.patch(
        f"/users/john@haag.de/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."
    # test with non-existing claim
    response = await full_client.patch(
        f"/users/{user_id}/claims/invalid-claim-id", json=patch_data
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user claim was not found."


async def test_delete_claim(full_client: FullClient):
    """Test that deleting a user claim works."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao

    user_id = "john@ghga.de"

    # post two different claims
    claim1 = ROLE_CLAIM_DATA.copy()
    claim2 = ROLE_CLAIM_DATA.copy()
    claim2["visa_type"] = "ResearcherStatus"
    for claim in (claim1, claim2):
        response = await full_client.post(f"/users/{user_id}/claims", json=claim)
        assert response.status_code == status.HTTP_201_CREATED
        claim_id = response.json()["id"]
        assert claim_id
        claim["id"] = claim_id

    # test deletion of first claim with non-existing user
    claim_id = claim1["id"]
    response = await full_client.delete(f"/users/john@haag.de/claims/{claim_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # test that claims have been posted
    response = await full_client.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 2

    # delete first claim properly
    response = await full_client.delete(f"/users/{user_id}/claims/{claim_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # test that claim has been deleted
    response = await full_client.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]
    assert claim["id"] == claim2["id"]
    assert claim["visa_type"] == "ResearcherStatus"

    # delete again
    response = await full_client.delete(f"/users/{user_id}/claims/{claim_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # delete second claim
    claim_id = claim2["id"]
    response = await full_client.delete(f"/users/{user_id}/claims/{claim_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # test that claim has been deleted
    response = await full_client.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 0

    # delete again
    response = await full_client.delete(f"/users/{user_id}/claims/{claim_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_grant_download_access(full_client: FullClient):
    """Test that granting access to a dataset works."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_as_utc()
    iva = Iva(
        id="some-iva-id",
        user_id="john@ghga.de",
        value="(0123)456789",
        type=IvaType.PHONE,
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    iva_dao = DummyIvaDao([iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    validity = {
        "valid_from": f"{now.year - 1}-01-01T00:00:00Z",
        "valid_until": f"{now.year + 1}-12-31T23:59:59Z",
    }

    # try to grant access using an invalid dataset accession
    response = await full_client.post(
        "/download-access/users/john@ghga.de/ivas/some-iva-id/datasets/not-a-dataset-id",
        json=validity,
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # now try again with a valid dataset accession
    response = await full_client.post(
        "/download-access/users/john@ghga.de/ivas/some-iva-id/datasets/DS0815",
        json=validity,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = await full_client.get("/users/john@ghga.de/claims")
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
        "user_id": "john@ghga.de",
        "iva_id": "some-iva-id",
        "valid_from": validity["valid_from"],
        "valid_until": validity["valid_until"],
        "visa_type": DATASET_CLAIM_DATA["visa_type"],
        "visa_value": DATASET_CLAIM_DATA["visa_value"],
    }

    response = await full_client.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ["DS0815"]


async def test_grant_download_access_with_unverified_iva(full_client: FullClient):
    """Test granting access to a dataset when the IVA is not yet verified."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_as_utc()
    iva = Iva(
        id="some-iva-id",
        user_id="john@ghga.de",
        value="(0123)456789",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    iva_dao = DummyIvaDao([iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    validity = {
        "valid_from": f"{now.year - 1}-01-01T00:00:00Z",
        "valid_until": f"{now.year + 1}-12-31T23:59:59Z",
    }

    response = await full_client.post(
        "/download-access/users/john@ghga.de/ivas/some-iva-id/datasets/DS0815",
        json=validity,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = await full_client.get("/users/john@ghga.de/claims")
    assert response.status_code == status.HTTP_200_OK
    requested_claims = response.json()

    assert len(requested_claims) == 1
    claim_data = requested_claims[0]
    assert claim_data["user_id"] == "john@ghga.de"
    assert claim_data["iva_id"] == "some-iva-id"

    response = await full_client.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


async def test_grant_download_access_without_iva(full_client: FullClient):
    """Test granting access to a dataset when the IVA does not exist."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    iva_dao = DummyIvaDao()
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    year = now_as_utc().year
    validity = {
        "valid_from": f"{year - 1}-01-01T00:00:00Z",
        "valid_until": f"{year + 1}-12-31T23:59:59Z",
    }

    response = await full_client.post(
        "/download-access/users/john@ghga.de/ivas/some-iva-id/datasets/DS0815",
        json=validity,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The IVA was not found."

    response = await full_client.get("/users/john@ghga.de/claims")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    response = await full_client.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


async def test_check_download_access(full_client: FullClient):
    """Test that checking download access for a single dataset works."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_as_utc()
    iva = Iva(
        id="some-iva-id",
        user_id="john@ghga.de",
        value="(0123)456789",
        type=IvaType.PHONE,
        state=IvaState.VERIFIED,
        created=now,
        changed=now,
    )
    iva_dao = DummyIvaDao([iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # post valid access permission for some-iva-id and DS0815

    current_timestamp = int(now.timestamp())
    claim_data: dict[str, Any] = {
        **DATASET_CLAIM_DATA,
        "iva_id": "some-iva-id",
        "valid_from": current_timestamp,
        "valid_until": current_timestamp + 60,
    }

    response = await full_client.post("/users/john@ghga.de/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0815"
    assert claim["user_id"] == "john@ghga.de"

    # post invalid access permission for DS0814

    claim_data["visa_value"] = claim_data["visa_value"].replace("0815", "0814")
    claim_data["valid_from"] = current_timestamp - 60
    claim_data["valid_until"] = current_timestamp - 30

    response = await full_client.post("/users/john@ghga.de/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0814"
    assert claim["user_id"] == "john@ghga.de"

    # check access for wrong user

    response = await full_client.get(
        "/download-access/users/jane@ghga.de/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."

    # check access for right user

    response = await full_client.get(
        "/download-access/users/john@ghga.de/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True

    # check access for invalid dataset accession

    response = await full_client.get(
        "/download-access/users/john@ghga.de/datasets/not-a-dataset-id"
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # check access when permission exists but is not valid any more

    response = await full_client.get(
        "/download-access/users/john@ghga.de/datasets/DS0814"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is False

    # check access when dataset and permission does not exist

    response = await full_client.get(
        "/download-access/users/john@ghga.de/datasets/DS0816"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is False

    # check that access is denied when user is not active

    user_dao.users[0] = user_dao.users[0].model_copy(
        update={"status": UserStatus.INACTIVE}
    )
    response = await full_client.get(
        "/download-access/users/john@ghga.de/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


async def test_check_download_access_with_unverified_iva(full_client: FullClient):
    """Test checking download access for a single dataset with an unverified IVA."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_as_utc()
    iva = Iva(
        id="some-iva-id",
        user_id="john@ghga.de",
        value="(0123)456789",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    iva_dao = DummyIvaDao([iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # post valid access permission for some-iva-id and DS0815

    current_timestamp = int(now.timestamp())
    claim_data: dict[str, Any] = {
        **DATASET_CLAIM_DATA,
        "iva_id": "some-iva-id",
        "valid_from": current_timestamp,
        "valid_until": current_timestamp + 60,
    }

    response = await full_client.post("/users/john@ghga.de/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0815"
    assert claim["user_id"] == "john@ghga.de"

    # check that access is not given when the IVA is not verified

    response = await full_client.get(
        "/download-access/users/john@ghga.de/datasets/DS0815"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is False


async def test_get_datasets_with_download_access(full_client: FullClient):
    """Test that getting all datasets with download access works."""
    user_dao = DummyUserDao()
    full_client.app.dependency_overrides[get_user_dao] = lambda: user_dao
    now = now_as_utc()
    unverified_iva = Iva(
        id="unverified-iva-id",
        user_id="john@ghga.de",
        value="(0123)456789",
        type=IvaType.PHONE,
        created=now,
        changed=now,
    )
    verified_iva = unverified_iva.model_copy(
        update={"id": "verified-iva-id", "state": IvaState.VERIFIED}
    )
    iva_dao = DummyIvaDao([unverified_iva, verified_iva])
    full_client.app.dependency_overrides[get_iva_dao] = lambda: iva_dao

    # should not have downloadable datasets in the beginning

    response = await full_client.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    # post valid access permission for DS0815

    current_timestamp = int(now.timestamp())
    some_claim_data: dict[str, Any] = {
        **DATASET_CLAIM_DATA,
        "iva_id": "verified-iva-id",
        "valid_from": current_timestamp,
        "valid_until": current_timestamp + 60,
    }

    response = await full_client.post(
        "/users/john@ghga.de/claims", json=some_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == "john@ghga.de"
    assert claim["iva_id"] == "verified-iva-id"
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0815"

    # post valid access permission for DS0816

    another_claim_data = {
        **some_claim_data,
        "visa_value": some_claim_data["visa_value"].replace("0815", "0816"),
    }
    response = await full_client.post(
        "/users/john@ghga.de/claims", json=another_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == "john@ghga.de"
    assert claim["iva_id"] == "verified-iva-id"
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0816"
    assert claim["user_id"] == "john@ghga.de"

    # post valid access permission with unverified IVA for DS0817

    yet_another_claim_data = {
        **some_claim_data,
        "iva_id": "unverified-iva-id",
        "visa_value": some_claim_data["visa_value"].replace("0815", "0817"),
    }

    response = await full_client.post(
        "/users/john@ghga.de/claims", json=yet_another_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == "john@ghga.de"
    assert claim["iva_id"] == "unverified-iva-id"
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0817"

    # post valid access permission for different user for DS0818

    foreign_claim_data = {
        **some_claim_data,
        "visa_value": some_claim_data["visa_value"].replace("0815", "0818"),
    }
    # pretend for the next query that Jane exists
    users = user_dao.users
    users.append(users[0].model_copy(update={"id": "jane@ghga.de"}))
    response = await full_client.post(
        "/users/jane@ghga.de/claims", json=foreign_claim_data
    )
    users.pop()

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == "jane@ghga.de"
    assert claim["iva_id"] == "verified-iva-id"
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0818"

    # post invalid access permission for DS0814

    former_claim_data = {
        **some_claim_data,
        "iva_id": "unverified-iva-id",
        "valid_from": current_timestamp - 60,
        "valid_until": current_timestamp - 30,
        "visa_value": some_claim_data["visa_value"].replace("0815", "0814"),
    }

    response = await full_client.post(
        "/users/john@ghga.de/claims", json=former_claim_data
    )

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["user_id"] == "john@ghga.de"
    assert claim["iva_id"] == "unverified-iva-id"
    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/DS0814"

    # get list of all claims

    response = await full_client.get("/users/john@ghga.de/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 4
    dataset_ids = {claim["visa_value"].rsplit("/", 1)[-1] for claim in response.json()}
    assert dataset_ids == {
        "DS0814",
        "DS0815",
        "DS0816",
        "DS0817",
    }

    # check access for wrong user
    response = await full_client.get("/download-access/users/jane@ghga.de/datasets")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."

    # check access for right user
    response = await full_client.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_200_OK
    dataset_ids = response.json()

    assert isinstance(dataset_ids, list)
    assert sorted(dataset_ids) == ["DS0815", "DS0816"]

    # check that access is denied when user is not active
    user_dao.users[0] = user_dao.users[0].model_copy(
        update={"status": UserStatus.INACTIVE}
    )
    response = await full_client.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


async def test_get_claims_for_seeded_data_steward(full_client: FullClient):
    """Test that the database is seeded with the configured data steward."""
    response = await full_client.get("/users/the-id-of-rod-steward/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]

    assert claim.pop("id")
    assert claim.pop("iva_id")
    assertion_date = claim.pop("assertion_date")
    assert claim.pop("creation_date") == assertion_date
    assert claim.pop("valid_from") == assertion_date
    assert claim.pop("valid_until") > assertion_date
    assert claim == {
        "asserted_by": "system",
        "conditions": None,
        "revocation_date": None,
        "user_id": "the-id-of-rod-steward",
        "source": "https://ghga.de",
        "sub_source": None,
        "visa_type": "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0",
        "visa_value": "data_steward@ghga.de",
    }
