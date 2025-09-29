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

"""Test the API of the work package service."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import status
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.jwt_helpers import decode_and_validate_token
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec
from pytest_httpx import HTTPXMock

from wps.config import Config
from wps.constants import WORK_ORDER_TOKEN_VALID_SECONDS
from wps.core.models import DatasetWithExpiration

from .fixtures import (  # noqa: F401
    FILE_BOX_ID,
    RDU_BOX_ID,
    SIGNING_KEY_PAIR,
    USER_ID,
    fixture_auth_headers,
    fixture_bad_auth_headers,
    fixture_client,
    fixture_config,
    fixture_repository,
    headers_for_token,
    non_mocked_hosts,
)
from .fixtures.crypt import decrypt, user_public_crypt4gh_key
from .fixtures.datasets import DATASET

pytestmark = pytest.mark.asyncio()


DOWNLOAD_ACCESS_URL = "http://access/download-access"
UPLOAD_ACCESS_URL = "http://access/upload-access"
DATASET_CREATION_DATA = {
    "dataset_id": "some-dataset-id",
    "type": "download",
    "file_ids": ["file-id-1", "file-id-3", "file-id-5"],
    "user_public_crypt4gh_key": user_public_crypt4gh_key,
}

TIMEOUT = 5


async def test_health_check(client: AsyncTestClient):
    """Test that the health check endpoint works."""
    response = await client.get("/health", timeout=TIMEOUT)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


async def test_create_work_package_unauthorized(
    client: AsyncTestClient, bad_auth_headers: dict[str, str]
):
    """Test that creating a work package needs authorization."""
    response = await client.post("/work-packages", json=DATASET_CREATION_DATA)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    response = await client.post(
        "/work-packages", json=DATASET_CREATION_DATA, headers=bad_auth_headers
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_get_work_package_unauthorized(client: AsyncTestClient):
    """Test that getting a work package needs authorization."""
    response = await client.get("/work-packages/some-work-package-id")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_make_download_work_order_token(
    client: AsyncTestClient,
    auth_headers: dict[str, str],
    httpx_mock: HTTPXMock,
    mongodb_populated: MongoDbFixture,
    config: Config,
):
    """Test that download-type work order tokens can be properly created."""
    # mock the access check for the test dataset to grant access
    url = f"{DOWNLOAD_ACCESS_URL}/users/{USER_ID}/datasets/some-dataset-id"
    valid_until = (now_utc_ms_prec() + timedelta(days=365)).isoformat()
    httpx_mock.add_response(method="GET", url=url, json=valid_until)

    # create a work package
    response = await client.post(
        "/work-packages", json=DATASET_CREATION_DATA, headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED

    response_data = response.json()
    assert isinstance(response_data, dict)
    assert sorted(response_data) == ["expires", "id", "token"]

    valid_timedelta = (
        datetime.fromisoformat(response_data["expires"]) - now_utc_ms_prec()
    )
    valid_days = round((valid_timedelta).total_seconds() / (24 * 60 * 60))

    assert valid_days == config.work_package_valid_days
    work_package_id = response_data["id"]
    assert (
        work_package_id
        and isinstance(work_package_id, str)
        and work_package_id.isascii()
    )

    token = response_data["token"]
    assert token and isinstance(token, str) and token.isascii()
    token = decrypt(token)
    assert token.isalnum() and len(token) == 24

    # try to get the work package without authorization
    response = await client.get(f"/work-packages/{work_package_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # try to get a non-existing work package with authorization and malformed ID
    response = await client.get(
        "/work-packages/some-work-package-id", headers=headers_for_token(token)
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # try to get a non-existing work package with authorization
    response = await client.get(
        f"/work-packages/{uuid4()}", headers=headers_for_token(token)
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # get the proper work package with authorization
    response = await client.get(
        f"/work-packages/{work_package_id}", headers=headers_for_token(token)
    )
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert isinstance(response_data, dict)
    assert sorted(response_data) == [
        "created",
        "expires",
        "files",
        "type",
    ]

    assert response_data.pop("created") < response_data.pop("expires")
    assert response_data == {
        "type": "download",
        "files": {"file-id-1": ".json", "file-id-3": ".bam"},
    }

    # try to get a work order token without authorization
    response = await client.post(
        f"/work-packages/{work_package_id}/files/file-id-1/work-order-tokens"
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # try to get a work order token for a non-existing work package with authorization
    response = await client.post(
        f"/work-packages/{uuid4()}/files/file-id-1/work-order-tokens",
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # try to get a work order token for a non-requested file with authorization
    response = await client.post(
        f"/work-packages/{work_package_id}/files/file-id-2/work-order-tokens",
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # try to get a work order token for a non-existing file with authorization
    response = await client.post(
        f"/work-packages/{work_package_id}/files/file-id-5/work-order-tokens",
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # get a work order token for an existing file with authorization
    response = await client.post(
        f"/work-packages/{work_package_id}/files/file-id-3/work-order-tokens",
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert "Cache-Control" in response.headers
    cache_control = response.headers["Cache-Control"]
    assert cache_control == f"max-age={WORK_ORDER_TOKEN_VALID_SECONDS}, private"

    wot = response.json()
    assert isinstance(wot, str)

    # decrypt the work order token
    assert wot and isinstance(wot, str) and wot.isascii()
    wot = decrypt(wot)

    # validate the work order token
    assert isinstance(wot, str)
    assert len(wot) > 80
    assert wot.count(".") == 2
    wot_chars = wot.replace(".", "").replace("-", "").replace("_", "")
    assert wot_chars.isalnum()
    assert wot_chars.isascii()
    wot_dict = decode_and_validate_token(wot, SIGNING_KEY_PAIR.public())

    # check the content of the work order token
    assert isinstance(wot_dict, dict)
    assert wot_dict.pop("exp") - wot_dict.pop("iat") == 30
    assert wot_dict == {
        "work_type": "download",
        "file_id": "file-id-3",
        "user_public_crypt4gh_key": user_public_crypt4gh_key,
    }

    # mock the access check for the test dataset to revoke access
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{USER_ID}/datasets/some-dataset-id",
        text="false",
    )

    # try to fetch a work order token again
    response = await client.post(
        f"/work-packages/{work_package_id}/files/file-id-3/work-order-tokens",
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Download access has been revoked" in response.json()["detail"]


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_make_upload_work_order_token(
    client: AsyncTestClient,
    auth_headers: dict[str, str],
    httpx_mock: HTTPXMock,
    mongodb_populated: MongoDbFixture,
    config: Config,
):
    """Test that upload-type work order tokens can be created."""
    # Mock upload access check to grant access
    valid_until = (now_utc_ms_prec() + timedelta(days=365)).isoformat()
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{USER_ID}/boxes/{RDU_BOX_ID}",
        json=valid_until,
    )

    # Create an upload work package
    upload_creation_data = {
        "box_id": RDU_BOX_ID,
        "type": "upload",
        "user_public_crypt4gh_key": user_public_crypt4gh_key,
    }

    response = await client.post(
        "/work-packages", json=upload_creation_data, headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED

    response_data = response.json()
    work_package_id = response_data["id"]
    token = decrypt(response_data["token"])

    # Test CREATE work order token
    create_request = {"work_type": "create", "alias": "test-file"}
    response = await client.post(
        f"/work-packages/{work_package_id}/boxes/{RDU_BOX_ID}/work-order-tokens",
        json=create_request,
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_201_CREATED
    create_wot = response.json()
    assert isinstance(create_wot, str)

    # Decrypt and validate the CREATE work order token
    decrypted_wot = decrypt(create_wot)
    wot_dict = decode_and_validate_token(decrypted_wot, SIGNING_KEY_PAIR.public())
    assert wot_dict["work_type"] == "create"
    assert wot_dict["alias"] == "test-file"
    assert wot_dict["user_public_crypt4gh_key"] == user_public_crypt4gh_key
    assert wot_dict["box_id"] == FILE_BOX_ID

    # Test UPLOAD work order token
    test_file_id = str(uuid4())
    upload_request = {"work_type": "upload", "file_id": test_file_id}
    response = await client.post(
        f"/work-packages/{work_package_id}/boxes/{RDU_BOX_ID}/work-order-tokens",
        json=upload_request,
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_201_CREATED

    upload_wot = response.json()
    decrypted_wot = decrypt(upload_wot)
    wot_dict = decode_and_validate_token(decrypted_wot, SIGNING_KEY_PAIR.public())
    assert wot_dict["work_type"] == "upload"
    assert wot_dict["file_id"] == test_file_id
    assert wot_dict["box_id"] == FILE_BOX_ID

    # Test CLOSE work order token
    close_request = {"work_type": "close", "file_id": test_file_id}
    response = await client.post(
        f"/work-packages/{work_package_id}/boxes/{RDU_BOX_ID}/work-order-tokens",
        json=close_request,
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_201_CREATED

    close_wot = response.json()
    decrypted_wot = decrypt(close_wot)
    wot_dict = decode_and_validate_token(decrypted_wot, SIGNING_KEY_PAIR.public())
    assert wot_dict["work_type"] == "close"
    assert wot_dict["file_id"] == test_file_id
    assert wot_dict["user_public_crypt4gh_key"] == user_public_crypt4gh_key
    assert wot_dict["box_id"] == FILE_BOX_ID

    # Test DELETE work order token
    delete_file_id = str(uuid4())
    delete_request = {"work_type": "delete", "file_id": delete_file_id}

    response = await client.post(
        f"/work-packages/{work_package_id}/boxes/{RDU_BOX_ID}/work-order-tokens",
        json=delete_request,
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_201_CREATED

    delete_wot = response.json()
    decrypted_wot = decrypt(delete_wot)
    wot_dict = decode_and_validate_token(decrypted_wot, SIGNING_KEY_PAIR.public())
    assert wot_dict["work_type"] == "delete"
    assert wot_dict["file_id"] == delete_file_id
    assert wot_dict["user_public_crypt4gh_key"] == user_public_crypt4gh_key
    assert wot_dict["box_id"] == FILE_BOX_ID

    # Test unauthorized access (wrong work package)
    response = await client.post(
        f"/work-packages/{uuid4()}/boxes/{RDU_BOX_ID}/work-order-tokens",
        json=create_request,
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_get_datasets_unauthenticated(client: AsyncTestClient):
    """Test that the list of accessible datasets cannot be fetched unauthenticated."""
    response = await client.get("/users/a86f8281-e18a-429e-88a9-a5c8ea0cf754/datasets")
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_get_datasets_for_another_user(
    client: AsyncTestClient, auth_headers: dict[str, str]
):
    """Test that the list of accessible datasets for another user cannot be fetched."""
    response = await client.get(
        "/users/78b1c9a5-eb59-4e49-9330-9ffdd2b161ef/datasets", headers=auth_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_get_datasets_when_none_authorized(
    client: AsyncTestClient,
    auth_headers: dict[str, str],
    httpx_mock: HTTPXMock,
    mongodb_populated: MongoDbFixture,
):
    """Test that no datasets are fetched when none are accessible."""
    # mock the access check for the test dataset
    expires = (now_utc_ms_prec() + timedelta(days=365)).isoformat()
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{USER_ID}/datasets",
        json={"some-other-dataset-id": expires},
    )

    # get the list of datasets

    response = await client.get(f"/users/{USER_ID}/datasets", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert isinstance(response_data, list)
    assert response_data == []


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_get_upload_wot_expired_access(
    client: AsyncTestClient,
    auth_headers: dict[str, str],
    httpx_mock: HTTPXMock,
    mongodb_populated: MongoDbFixture,
    config: Config,
):
    """Test that access is rejected when a user tries to get a WOT for an upload box
    for which they previously had access, but which has since expired.
    """
    # Mock initial upload access check to grant access
    valid_until = (now_utc_ms_prec() + timedelta(days=365)).isoformat()
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{USER_ID}/boxes/{RDU_BOX_ID}",
        json=valid_until,
    )

    # Create an upload work package
    upload_creation_data = {
        "box_id": RDU_BOX_ID,
        "type": "upload",
        "user_public_crypt4gh_key": user_public_crypt4gh_key,
    }

    response = await client.post(
        "/work-packages", json=upload_creation_data, headers=auth_headers
    )
    assert response.status_code == status.HTTP_201_CREATED

    response_data = response.json()
    work_package_id = response_data["id"]
    token = decrypt(response_data["token"])

    # Mock expired access check - return null to indicate no access
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{USER_ID}/boxes/{RDU_BOX_ID}",
        text="null",
    )

    # Try to create a work order token - should fail due to expired box access
    create_request = {"work_type": "create", "alias": "test-file"}

    response = await client.post(
        f"/work-packages/{work_package_id}/boxes/{RDU_BOX_ID}/work-order-tokens",
        json=create_request,
        headers=headers_for_token(token),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Upload access has been revoked" in response.json()["detail"]


async def test_get_datasets(
    client: AsyncTestClient,
    auth_headers: dict[str, str],
    httpx_mock: HTTPXMock,
    mongodb_populated: MongoDbFixture,
):
    """Test that the list of accessible datasets can be fetched."""
    # mock the access check for the test dataset

    expires = (now_utc_ms_prec() + timedelta(days=365)).isoformat()
    httpx_mock.add_response(
        method="GET",
        url=f"{DOWNLOAD_ACCESS_URL}/users/{USER_ID}/datasets",
        json={
            "some-dataset-id": expires,
            "some-non-existing-dataset-id": expires,
        },
    )

    # get the list of datasets
    response = await client.get(f"/users/{USER_ID}/datasets", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 1
    returned = response_data[0]
    expected = {**DATASET.model_dump(), "expires": expires}
    assert DatasetWithExpiration(**returned) == DatasetWithExpiration(**expected)


async def test_get_upload_boxes(
    client: AsyncTestClient,
    auth_headers: dict[str, str],
    httpx_mock: HTTPXMock,
    mongodb: MongoDbFixture,
    config: Config,
):
    """Test the endpoint for retrieving upload box access by user ID"""
    box_id1 = "91ba4d24-0bb6-4dd4-b80d-b0cf2421fb79"
    box_id2 = "40bdf805-7e85-45d1-9ad7-4f66b8fd9c7b"
    expires = (now_utc_ms_prec() + timedelta(days=180)).isoformat()
    httpx_mock.add_response(
        method="GET",
        url=f"{UPLOAD_ACCESS_URL}/users/{USER_ID}/boxes",
        json={
            box_id1: expires,
            box_id2: expires,
        },
    )

    # Insert boxes into the DB using the ids defined above
    box1 = {
        "_id": UUID(box_id1),
        "file_upload_box_id": uuid4(),
        "title": "Box1",
        "description": "This is box 1",
    }
    box2 = {
        "_id": UUID(box_id2),
        "file_upload_box_id": uuid4(),
        "title": "Box2",
        "description": "This is box 2",
    }
    box3 = {  # this one should be excluded
        "_id": uuid4(),
        "file_upload_box_id": uuid4(),
        "title": "Box3",
        "description": "This is box 3",
    }
    db = mongodb.client[config.db_name]
    collection = db[config.upload_boxes_collection]
    collection.insert_one(box1)
    collection.insert_one(box2)
    collection.insert_one(box3)

    response = await client.get(f"/users/{USER_ID}/boxes", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data
    assert isinstance(data, list)
    assert len(data) == 2
    assert {box["id"] for box in data} == {box_id1, box_id2}
