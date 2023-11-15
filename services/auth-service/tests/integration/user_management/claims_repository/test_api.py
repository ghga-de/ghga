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

"""Test the REST API"""

from datetime import datetime
from operator import itemgetter
from typing import Any

from fastapi import status
from ghga_service_commons.utils.utc_dates import now_as_utc

from auth_service.user_management.user_registry.deps import get_user_dao

from ....fixtures.utils import DummyUserDao
from .fixtures import (  # noqa: F401
    fixture_client,
    fixture_client_with_db,
    fixture_mongodb,
)

ROLE_CLAIM_DATA = {
    "visa_type": "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0",
    "visa_value": "data-steward@ghga.de",
    "valid_from": "2022-10-01T12:00:00Z",
    "valid_until": "2022-10-31T12:00:00Z",
    "assertion_date": "2022-09-01T12:00:00Z",
    "source": "https://ghga.de",
    "asserted_by": "system",
}

DATASET_CLAIM_DATA = {
    "visa_type": "ControlledAccessGrants",
    "visa_value": "https://ghga.de/datasets/some-dataset-id",
    "assertion_date": "2022-06-01T12:00:00Z",
    "source": "https://ghga.de",
    "asserted_by": "system",
}


def test_health_check(client):
    """Test that the health check endpoint works."""
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


def test_get_from_a_random_path(client):
    """Test that a GET request to a random path raises a not found error."""
    response = client.post("/some/random/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_post_claim(client_with_db):
    """Test that creating a user claim works."""
    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    response = client_with_db.post("/users/john@ghga.de/claims", json=ROLE_CLAIM_DATA)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED, claim

    claim_id = claim.pop("id", None)
    assert claim_id is not None
    assert len(claim_id) == 36
    assert claim_id.count("-") == 4
    assert claim.pop("user_id") == "john@ghga.de"
    assert claim.pop("sub_source") is None
    assert claim.pop("conditions") is None
    assert claim.pop("revocation_date") is None
    assert claim.pop("creation_date") is not None

    assert claim == ROLE_CLAIM_DATA

    # test with non-existing user
    response = client_with_db.post("/users/john@haag.de/claims", json=ROLE_CLAIM_DATA)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


def test_get_claims(client_with_db):
    """Test that getting all claims of a user works."""
    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

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
        response = client_with_db.post(f"/users/{user_id}/claims", json=claim)
        assert response.status_code == status.HTTP_201_CREATED
        posted_claims.append(response.json())

    response = client_with_db.get(f"/users/{user_id}/claims")
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
    response = client_with_db.get("/users/john@haag.de/claims")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."


def test_patch_claim(client_with_db):
    """Test that revoking a user claim works."""
    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    user_id = "john@ghga.de"

    # post test claim
    response = client_with_db.post(f"/users/{user_id}/claims", json=ROLE_CLAIM_DATA)
    posted_claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    claim_id = posted_claim["id"]
    assert claim_id is not None
    assert posted_claim.pop("revocation_date") is None

    # revoke test claim
    revocation_date = "2022-10-15T12:00:00Z"
    patch_data = {"revocation_date": revocation_date}
    response = client_with_db.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # test that claim has been revoked
    response = client_with_db.get(f"/users/{user_id}/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]
    assert claim.pop("revocation_date") == revocation_date
    assert claim == posted_claim

    # test without revocation date
    patch_data = {"revocation_date": None}  # type: ignore
    response = client_with_db.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # test with later revocation date
    patch_data = {"revocation_date": "2022-10-15T13:00:00Z"}
    response = client_with_db.patch(
        f"/users/{user_id}/claims/{claim_id}", json=patch_data
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["detail"] == "Already revoked earlier."

    # test with earlier revocation date
    revocation_date = "2022-10-15T11:00:00Z"
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
    assert claim == posted_claim

    # test with non-existing user
    response = client_with_db.patch(
        f"/users/john@haag.de/claims/{claim_id}", json=patch_data
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

    user_id = "john@ghga.de"

    # post two different claims
    claim1 = ROLE_CLAIM_DATA.copy()
    claim2 = ROLE_CLAIM_DATA.copy()
    claim2["visa_type"] = "ResearcherStatus"
    for claim in (claim1, claim2):
        response = client_with_db.post(f"/users/{user_id}/claims", json=claim)
        assert response.status_code == status.HTTP_201_CREATED
        claim_id = response.json()["id"]
        assert claim_id
        claim["id"] = claim_id

    # test deletion of first claim with non-existing user
    claim_id = claim1["id"]
    response = client_with_db.delete(f"/users/john@haag.de/claims/{claim_id}")
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
    assert claim["visa_type"] == "ResearcherStatus"

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


def test_grant_download_access(client_with_db):
    """Test that granting access to a dataset works."""
    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    current_date = now_as_utc()
    current_year = current_date.year
    validity = {
        "valid_from": f"{current_year - 1}-01-01T00:00:00Z",
        "valid_until": f"{current_year + 1}-12-31T23:59:59Z",
    }

    response = client_with_db.post(
        "/download-access/users/john@ghga.de/datasets/some-dataset-id",
        json=validity,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = client_with_db.get("/users/john@ghga.de/claims")
    assert response.status_code == status.HTTP_200_OK
    requested_claims = response.json()

    assert len(requested_claims) == 1

    claim_data = requested_claims[0]
    assert claim_data.pop("id")
    creation_date = claim_data.pop("creation_date")
    assert creation_date
    assert claim_data.pop("assertion_date") == creation_date
    creation_datetime = datetime.fromisoformat(creation_date.replace("Z", "+00:00"))
    assert 0 <= (creation_datetime - current_date).seconds < 5

    assert claim_data == {
        "asserted_by": "dac",
        "conditions": None,
        "revocation_date": None,
        "source": DATASET_CLAIM_DATA["source"],
        "sub_source": None,
        "user_id": "john@ghga.de",
        "valid_from": validity["valid_from"],
        "valid_until": validity["valid_until"],
        "visa_type": DATASET_CLAIM_DATA["visa_type"],
        "visa_value": DATASET_CLAIM_DATA["visa_value"],
    }

    response = client_with_db.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == ["some-dataset-id"]


def test_check_download_access(client_with_db):
    """Test that checking download access for a single dataset works."""
    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    # post valid access permission for some-dataset-id

    claim_data: dict[str, Any] = DATASET_CLAIM_DATA.copy()
    current_timestamp = now_as_utc().timestamp()
    claim_data["valid_from"] = current_timestamp
    claim_data["valid_until"] = current_timestamp + 60

    response = client_with_db.post("/users/john@ghga.de/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/some-dataset-id"
    assert claim["user_id"] == "john@ghga.de"

    # post invalid access permission for former-dataset-id

    claim_data["visa_value"] = claim_data["visa_value"].replace("some", "former")
    claim_data["valid_from"] = current_timestamp - 60
    claim_data["valid_until"] = current_timestamp - 30

    response = client_with_db.post("/users/john@ghga.de/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/former-dataset-id"
    assert claim["user_id"] == "john@ghga.de"

    # check access for wrong user

    response = client_with_db.get(
        "/download-access/users/jane@ghga.de/datasets/some-dataset-id"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."

    # check access for right user

    response = client_with_db.get(
        "/download-access/users/john@ghga.de/datasets/some-dataset-id"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True

    # check access when permission exists but is not valid any more

    response = client_with_db.get(
        "/download-access/users/john@ghga.de/datasets/former-dataset-id"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is False

    # check access when dataset and permission does not exist

    response = client_with_db.get(
        "/download-access/users/john@ghga.de/datasets/another-dataset-id"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is False


def test_get_datasets_with_download_access(client_with_db):
    """Test that getting all datasets with download access works."""
    user_dao = DummyUserDao()
    client_with_db.app.dependency_overrides[get_user_dao] = lambda: user_dao

    # should not have downloadable datasets in the beginning

    response = client_with_db.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

    # post valid access permission for some-dataset-id

    claim_data: dict[str, Any] = DATASET_CLAIM_DATA.copy()
    current_timestamp = now_as_utc().timestamp()
    claim_data["valid_from"] = current_timestamp
    claim_data["valid_until"] = current_timestamp + 60

    response = client_with_db.post("/users/john@ghga.de/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/some-dataset-id"
    assert claim["user_id"] == "john@ghga.de"

    # post valid access permission for another-dataset-id

    claim_data["visa_value"] = claim_data["visa_value"].replace("some", "another")

    response = client_with_db.post("/users/john@ghga.de/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/another-dataset-id"
    assert claim["user_id"] == "john@ghga.de"

    # post invalid access permission for former-dataset-id

    claim_data["visa_value"] = claim_data["visa_value"].replace("another", "former")
    claim_data["valid_from"] = current_timestamp - 60
    claim_data["valid_until"] = current_timestamp - 30

    response = client_with_db.post("/users/john@ghga.de/claims", json=claim_data)

    claim = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    assert claim["visa_type"] == "ControlledAccessGrants"
    assert claim["visa_value"] == "https://ghga.de/datasets/former-dataset-id"
    assert claim["user_id"] == "john@ghga.de"

    # check access for wrong user

    response = client_with_db.get("/download-access/users/jane@ghga.de/datasets")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "The user was not found."

    # check access for right user

    response = client_with_db.get("/download-access/users/john@ghga.de/datasets")
    assert response.status_code == status.HTTP_200_OK
    dataset_ids = response.json()

    assert isinstance(dataset_ids, list)
    assert sorted(dataset_ids) == ["another-dataset-id", "some-dataset-id"]


def test_get_claims_for_seeded_data_steward(client_with_db):
    """Test that the database is seeded with the configured data steward."""
    response = client_with_db.get("/users/the-id-of-rod-steward/claims")
    assert response.status_code == status.HTTP_200_OK
    claims = response.json()
    assert len(claims) == 1
    claim = claims[0]

    assert claim.pop("id")
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
