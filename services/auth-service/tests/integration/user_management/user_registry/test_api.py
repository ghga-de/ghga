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

from datetime import datetime

from fastapi import status
from ghga_service_chassis_lib.utils import now_as_utc

from auth_service.user_management.user_registry.utils import is_internal_id

from ..fixtures import (  # noqa: F401; pylint: disable=unused-import
    fixture_client,
    fixture_client_with_db,
)

MIN_USER_DATA = {
    "ls_id": "max@ls.org",
    "status": "activated",
    "name": "Max Headroom",
    "email": "max@example.org",
}

OPT_USER_DATA = {
    "title": "Dr.",
    "research_topics": "genes",
    "registration_reason": "for testing",
}

MAX_USER_DATA = {**MIN_USER_DATA, **OPT_USER_DATA}


def test_get_from_root(client):
    """Test that a simple GET request passes."""

    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == '"Index of the User Management Service"'


def test_get_from_some_other_path(client):
    """Test that a GET request to a random path raises a not found error."""

    response = client.post("/some/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_post_user(client_with_db):
    """Test that registering a user works."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data)

    user = response.json()
    assert response.status_code == status.HTTP_201_CREATED, user

    id_ = user.pop("id", None)
    assert is_internal_id(id_)

    assert user.pop("status_change") is None
    date_diff = now_as_utc() - datetime.fromisoformat(user.pop("registration_date"))
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == user_data

    response = client_with_db.post("/users", json=user_data)

    error = response.json()
    assert response.status_code == status.HTTP_409_CONFLICT, error
    assert error == {"detail": "User was already registered."}


def test_post_user_with_minimal_data(client_with_db):
    """Test that registering a user with minimal data works."""

    user_data = MIN_USER_DATA
    response = client_with_db.post("/users", json=user_data)

    user = response.json()
    assert response.status_code == status.HTTP_201_CREATED, user

    id_ = user.pop("id", None)
    assert is_internal_id(id_)

    assert user.pop("status_change") is None
    date_diff = now_as_utc() - datetime.fromisoformat(user.pop("registration_date"))
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == {**MIN_USER_DATA, **dict.fromkeys(OPT_USER_DATA)}  # type: ignore

    response = client_with_db.post("/users", json=user_data)

    error = response.json()
    assert response.status_code == status.HTTP_409_CONFLICT, error
    assert error == {"detail": "User was already registered."}


def test_post_user_with_invalid_email(client_with_db):
    """Test that registering a user with invalid email does not work."""

    user_data = {**MAX_USER_DATA, "email": "invalid"}
    response = client_with_db.post("/users", json=user_data)

    error = response.json()
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, error
    assert error["detail"][0]["msg"] == "value is not a valid email address"


def test_get_non_existing_user(client_with_db):
    """Test requesting a non-existing user."""

    response = client_with_db.get("/users/bad@example.org")

    error = response.json()
    assert response.status_code == status.HTTP_404_NOT_FOUND, error
    assert error == {"detail": "The user was not found."}


def test_get_user_via_id(client_with_db):
    """Test that a registered user can be found via internal ID."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data)
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    id_ = expected_user["id"]
    response = client_with_db.get(f"/users/{id_}")

    user = response.json()
    assert response.status_code == status.HTTP_200_OK, user

    assert user == expected_user


def test_get_user_via_ls_id(client_with_db):
    """Test that a registered user can be found via LS ID."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data)
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    id_ = expected_user["ls_id"]
    response = client_with_db.get(f"/users/{id_}")

    user = response.json()
    assert response.status_code == status.HTTP_200_OK, user

    assert user == expected_user


def test_patch_non_existing_user(client_with_db):
    """Test modifying a non-existing user."""

    update_data = {"title": "Prof."}
    response = client_with_db.patch("/users/foo-bar-baz-qux", json=update_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "The user was not found."}


def test_patch_user(client_with_db):
    """Test that a registered user can be modified."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data)
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    id_ = expected_user["id"]

    assert expected_user["status"] == MAX_USER_DATA["status"]
    assert expected_user.pop("status_change") is None

    update_data = {"status": "inactivated", "title": "Prof."}
    assert expected_user["status"] != update_data["status"]
    assert expected_user["title"] != update_data["title"]
    expected_user.update(update_data)

    response = client_with_db.patch(f"/users/{id_}", json=update_data)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = client_with_db.get(f"/users/{id_}")

    user = response.json()
    assert response.status_code == status.HTTP_200_OK, user

    status_change = user.pop("status_change")
    assert status_change["previous"] == MAX_USER_DATA["status"]
    assert status_change["by"] is None
    assert status_change["context"] == "manual change"
    date_diff = now_as_utc() - datetime.fromisoformat(status_change["change_date"])
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == expected_user


def test_patch_user_partially(client_with_db):
    """Test that a registered user can be modified partially."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data)
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    id_ = expected_user["id"]

    assert expected_user["status"] == MAX_USER_DATA["status"]
    assert expected_user.pop("status_change") is None

    update_data = {"status": "inactivated"}
    assert expected_user["status"] != update_data["status"]
    expected_user.update(update_data)

    response = client_with_db.patch(f"/users/{id_}", json=update_data)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = client_with_db.get(f"/users/{id_}")

    user = response.json()
    assert response.status_code == status.HTTP_200_OK, user

    status_change = user.pop("status_change")
    assert status_change["previous"] == MAX_USER_DATA["status"]
    assert status_change["by"] is None
    assert status_change["context"] == "manual change"
    date_diff = now_as_utc() - datetime.fromisoformat(status_change["change_date"])
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == expected_user

    update_data = {"title": "Prof."}
    assert expected_user["title"] != update_data["title"]
    expected_user.update(update_data)

    response = client_with_db.patch(f"/users/{id_}", json=update_data)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = client_with_db.get(f"/users/{id_}")

    user = response.json()
    assert response.status_code == status.HTTP_200_OK, user

    assert user.pop("status_change") == status_change

    assert user == expected_user


def test_delete_non_existing_user(client_with_db):
    """Test deleting a non-existing user."""

    response = client_with_db.delete("/users/foo-bar-baz-qux")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "The user was not found."}


def test_delete_user(client_with_db):
    """Test that a registered user can be deleted."""

    user_data = MIN_USER_DATA
    response = client_with_db.post("/users", json=user_data)
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    id_ = expected_user["id"]

    response = client_with_db.get(f"/users/{id_}")

    user = response.json()
    assert response.status_code == status.HTTP_200_OK, user

    response = client_with_db.delete(f"/users/{id_}")

    assert response.status_code == status.HTTP_204_NO_CONTENT, user
    assert not response.text

    response = client_with_db.get(f"/users/{id_}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "The user was not found."}

    response = client_with_db.delete(f"/users/{id_}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "The user was not found."}
