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

"""Test the core claims REST API"""

from operator import itemgetter

import pytest
from fastapi import status

from auth_service.user_registry.deps import get_user_dao

from ...fixtures.utils import DummyUserDao
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
