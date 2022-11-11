# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

from operator import itemgetter

from fastapi import status

from auth_service.user_management.user_registry.deps import get_user_dao

from ....fixtures.utils import DummyUserDao
from ..fixtures import (  # noqa: F401; pylint: disable=unused-import
    fixture_client,
    fixture_client_with_db,
)

CLAIM_DATA = dict(
    visa_type="GHGA_ROLE",
    visa_value="data-steward@ghga.de",
    assertion_date="2022-09-01T12:00:00",
    valid_from="2022-10-01T12:00:00",
    valid_until="2022-10-31T12:00:00",
    source="https://ghga.de",
)


def test_get_from_root(client):
    """Test that a simple GET request passes."""

    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == '"Index of the User Management Service"'


def test_get_from_some_other_path(client):
    """Test that a GET request to a random path raises a not found error."""

    response = client.post("/some/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_post_claim(client_with_db):
    """Test that posting a user claim works."""

    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    response = client_with_db.post("/users/john@ghga.org/claims", json=CLAIM_DATA)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED, claim

    claim_id = claim.pop("id", None)
    assert claim_id is not None
    assert len(claim_id) == 36
    assert claim_id.count("-") == 4
    assert claim.pop("user_id") == "john@ghga.org"
    assert claim.pop("sub_source") is None
    assert claim.pop("asserted_by") is None
    assert claim.pop("conditions") is None
    assert claim.pop("revocation_date") is None
    assert claim.pop("revocation_by") is None
    assert claim.pop("creation_date") is not None
    assert claim.pop("creation_by") is not None

    assert claim == CLAIM_DATA

    # test with non-existing user
    response = client_with_db.post("/users/john@aggh.org/claims", json=CLAIM_DATA)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


def test_get_claims(client_with_db):
    """Test that getting all claims of a user works."""

    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    user_id = "john@ghga.org"

    # post two different claims
    claim1 = CLAIM_DATA
    claim2 = {
        **claim1,
        "visa_type": "RESEARCHER_STATUS",
        "visa_value": "researcher@ghga.de",
    }
    posted_claims = []
    for claim in (claim1, claim2):
        response = client_with_db.post(f"/users/{user_id}/claims", json=claim)
        assert response.status_code == status.HTTP_201_CREATED
        posted_claims.append(response.json())
    posted_claims.sort(key=itemgetter("visa_type"))

    response = client_with_db.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    requested_claims = response.json()
    posted_claims.sort(key=itemgetter("visa_type"))

    assert requested_claims == posted_claims

    assert requested_claims[0]["user_id"] == user_id
    assert requested_claims[1]["user_id"] == user_id
    assert requested_claims[0]["visa_type"] == "GHGA_ROLE"
    assert requested_claims[1]["visa_type"] == "RESEARCHER_STATUS"
    assert requested_claims[0]["visa_value"] != requested_claims[1]["visa_value"]

    # test with non-existing user
    response = client_with_db.get("/users/john@aggh.org/claims")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


def test_patch_claim(client_with_db):
    """Test that revoking a user claim works."""

    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    user_id = "john@ghga.org"

    # post test claim
    response = client_with_db.post(f"/users/{user_id}/claims", json=CLAIM_DATA)
    posted_claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    claim_id = posted_claim["id"]
    assert claim_id is not None
    assert posted_claim.pop("revocation_date") is None
    assert posted_claim.pop("revocation_by") is None

    # revoke test claim
    revocation_date = "2022-10-15T12:00:00"
    patch_data = {"revocation_date": revocation_date}
    response = client_with_db.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # tset that claim has been revoked
    response = client_with_db.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]
    assert claim.pop("revocation_date") == revocation_date
    assert claim.pop("revocation_by") == "someone"  # needs to be changed
    assert claim == posted_claim

    # test without revocation date
    patch_data = {"revocation_date": None}  # type: ignore
    response = client_with_db.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # test with later revocation date
    patch_data = {"revocation_date": "2022-10-15T13:00:00"}
    response = client_with_db.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "Already revoked earlier."

    # test with earlier revocation date
    revocation_date = "2022-10-15T11:00:00"
    patch_data = {"revocation_date": revocation_date}
    response = client_with_db.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # test that revocation was advanced
    response = client_with_db.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]
    assert claim.pop("revocation_date") == revocation_date
    assert claim.pop("revocation_by") == "someone"  # needs to be changed
    assert claim == posted_claim

    # test with non-existing user
    response = client_with_db.patch(
        f"/users/john@aggh.org/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."
    # test with non-existing claim
    response = client_with_db.patch(
        f"/users/{user_id}/claims/invalid-claim-id", json=patch_data
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user claim was not found."


def test_delete_claim(client_with_db):
    """Test that deleting a user claim works."""

    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    user_id = "john@ghga.org"

    # post two different claims
    claim1 = CLAIM_DATA.copy()
    claim2 = CLAIM_DATA.copy()
    claim2["visa_type"] = "RESEARCHER_STATUS"
    for claim in (claim1, claim2):
        response = client_with_db.post(f"/users/{user_id}/claims", json=claim)
        assert response.status_code == status.HTTP_201_CREATED
        claim_id = response.json()["id"]
        assert claim_id
        claim["id"] = claim_id

    # test deletion of first claim with non-existing user
    claim_id = claim1["id"]
    response = client_with_db.delete(f"/users/john@aggh.org/claims/{claim_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # test that claims have been posted
    response = client_with_db.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 2

    # delete first claim properly
    response = client_with_db.delete(f"/users/{user_id}/claims/{claim_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # test that claim has been deleted
    response = client_with_db.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]
    assert claim["id"] == claim2["id"]
    assert claim["visa_type"] == "RESEARCHER_STATUS"

    # delete again
    response = client_with_db.delete(f"/users/{user_id}/claims/{claim_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    # delete second claim
    claim_id = claim2["id"]
    response = client_with_db.delete(f"/users/{user_id}/claims/{claim_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # test that claim has been deleted
    response = client_with_db.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 0

    # delete again
    response = client_with_db.delete(f"/users/{user_id}/claims/{claim_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
