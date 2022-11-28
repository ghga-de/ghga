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

from ....fixtures.utils import get_headers_for
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


def test_health_check(client):
    """Test that the health check endpoint works."""

    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


def test_get_from_a_random_path(client):
    """Test that a GET request to a random path raises a not found error."""

    response = client.post("/some/random/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_post_user(client_with_db, user_headers):
    """Test that registering a user works."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()

    id_ = user.pop("id", None)
    assert is_internal_id(id_)

    assert user.pop("status_change") is None
    date_diff = now_as_utc() - datetime.fromisoformat(user.pop("registration_date"))
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == user_data

    response = client_with_db.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    error = response.json()
    assert error == {"detail": "User was already registered."}


def test_post_user_with_minimal_data(client_with_db, user_headers):
    """Test that registering a user with minimal data works."""

    user_data = MIN_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()

    id_ = user.pop("id", None)
    assert is_internal_id(id_)

    assert user.pop("status_change") is None
    date_diff = now_as_utc() - datetime.fromisoformat(user.pop("registration_date"))
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == {**MIN_USER_DATA, **dict.fromkeys(OPT_USER_DATA)}  # type: ignore

    response = client_with_db.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_409_CONFLICT
    error = response.json()
    assert error == {"detail": "User was already registered."}


def test_post_user_with_different_name(client, user_headers):
    """Test that registering a user with different name does not work."""

    user_data = {**MAX_USER_DATA, "name": "Max Liebermann"}
    response = client.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error = response.json()
    assert error["detail"] == "User cannot be registered."


def test_post_user_with_different_email(client, user_headers):
    """Test that registering a user with different email does not work."""

    user_data = {**MAX_USER_DATA, "email": "max@fake.org"}
    response = client.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error = response.json()
    assert error["detail"] == "User cannot be registered."


def test_post_user_with_invalid_email(client, user_headers):
    """Test that registering a user with invalid email does not work."""

    user_data = {**MAX_USER_DATA, "email": "invalid"}
    response = client.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert error["detail"][0]["msg"] == "value is not a valid email address"


def test_post_user_with_different_ls_id(client, user_headers):
    """Test that registering a user with a different LS ID does not work."""

    user_data = {**MAX_USER_DATA, "ls_id": "frodo@ls.org"}
    response = client.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authorized to register user."


def test_post_user_unathenticated(client_with_db, user_headers):
    """Test that registering a user without authentication does not work."""

    response = client_with_db.post("/users", json=MAX_USER_DATA)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authenticated"


def test_get_non_existing_user(client_with_db, steward_headers):
    """Test requesting a non-existing user."""

    response = client_with_db.get("/users/bad@example.org", headers=steward_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


def test_get_different_user(client, user_headers):
    """Test requesting a different user."""

    response = client.get("/users/other@example.org", headers=user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to request user."}

    response = client.get("/users/max-internal", headers=user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to request user."}


def test_get_user_via_id(client_with_db, user_headers):
    """Test that a registered user can be found via internal ID."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()

    id_ = expected_user["id"]
    response = client_with_db.get(f"/users/{id_}", headers=user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to request user."}

    headers = get_headers_for(id=id_, name="Max Headroom", email="max@example.org")
    response = client_with_db.get(f"/users/{id_}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user == expected_user


def test_get_user_via_ls_id(client_with_db, user_headers):
    """Test that a registered user can be found via LS ID."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    id_ = expected_user["ls_id"]
    response = client_with_db.get(f"/users/{id_}", headers=user_headers)

    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user == expected_user


def test_get_different_user_as_data_steward(
    client_with_db, user_headers, steward_headers
):
    """Test requesting a different user as a data steward."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()

    id_ = expected_user["ls_id"]
    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)

    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user == expected_user

    id_ = expected_user["id"]
    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)

    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user == expected_user


def test_get_user_unauthenticated(client):
    """Test requesting a user without authentication."""

    response = client.get("/users/bad@example.org")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}


def test_patch_non_existing_user(client_with_db, steward_headers):
    """Test modifying a non-existing user."""

    update_data = {"title": "Prof."}
    response = client_with_db.patch(
        "/users/foo-bar-baz-qux", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


def test_patch_user_as_data_steward(client_with_db, user_headers, steward_headers):
    """Test that a data steward can modify a registered user."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    id_ = expected_user["id"]

    assert expected_user["status"] == MAX_USER_DATA["status"]
    assert expected_user.pop("status_change") is None

    update_data = {"status": "inactivated", "title": "Prof."}
    assert expected_user["status"] != update_data["status"]
    assert expected_user["title"] != update_data["title"]
    expected_user.update(update_data)

    response = client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # request user as data steward to check modification
    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    # can get status change as data steward
    status_change = user.pop("status_change")
    assert status_change["previous"] == MAX_USER_DATA["status"]
    assert status_change["by"] == "steve-internal"
    assert status_change["context"] == "manual change"
    date_diff = now_as_utc() - datetime.fromisoformat(status_change["change_date"])
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == expected_user

    # request user as same user
    headers = get_headers_for(id=id_, name="Max Headroom", email="max@example.org")
    response = client_with_db.get(f"/users/{id_}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    # cannot get status change as normal user
    assert user.pop("status_change") is None
    date_diff = now_as_utc() - datetime.fromisoformat(status_change["change_date"])
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == expected_user


def test_patch_user_partially(client_with_db, user_headers, steward_headers):
    """Test that a data steward can modify a registered user partially."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()
    id_ = expected_user["id"]

    assert expected_user["status"] == MAX_USER_DATA["status"]
    assert expected_user.pop("status_change") is None

    update_data = {"status": "inactivated"}
    assert expected_user["status"] != update_data["status"]
    expected_user.update(update_data)

    response = client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    status_change = user.pop("status_change")
    assert status_change["previous"] == MAX_USER_DATA["status"]
    assert status_change["by"] == "steve-internal"
    assert status_change["context"] == "manual change"
    date_diff = now_as_utc() - datetime.fromisoformat(status_change["change_date"])
    assert 0 <= date_diff.total_seconds() <= 10

    assert user == expected_user

    update_data = {"title": "Prof."}
    assert expected_user["title"] != update_data["title"]
    expected_user.update(update_data)

    response = client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user.pop("status_change") == status_change

    assert user == expected_user


def test_patch_user_as_same_user(client_with_db, user_headers, steward_headers):
    """Test that users can modify their title, but not their status."""

    user_data = MAX_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()
    id_ = expected_user["id"]

    # check that users cannot change their own status
    update_data = {"status": "inactivated"}
    assert expected_user["status"] != update_data["status"]
    headers = get_headers_for(id=id_, name="Max Headroom", email="max@example.org")
    response = client_with_db.patch(f"/users/{id_}", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to make this modification."}
    # check that they cannot even change their status as data stewards
    headers = get_headers_for(
        id=id_, name="Max Headroom", email="max@example.org", role="data_steward"
    )
    response = client_with_db.patch(f"/users/{id_}", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to make this modification."}

    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()
    assert user == expected_user

    # check that users can change their title
    update_data = {"title": "Prof."}
    assert expected_user["title"] != update_data["title"]
    expected_user.update(update_data)
    headers = get_headers_for(id=id_, name="Max Headroom", email="max@example.org")
    response = client_with_db.patch(f"/users/{id_}", json=update_data, headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)

    assert response.status_code == status.HTTP_200_OK
    user = response.json()
    assert user == expected_user


def test_patch_different_user_as_normal_user(client, user_headers):
    """Test that normal users cannot modify other users."""

    update_data = {"title": "Prof."}
    response = client.patch(
        "/users/somebody-else", json=update_data, headers=user_headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to make this modification."}


def test_patch_user_unauthenticated(client):
    """Test that modifying a user without authentication does not work."""

    update_data = {"title": "Prof."}
    response = client.patch("/users/foo-bar-baz-qux", json=update_data)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}


def test_delete_non_existing_user(client, steward_headers):
    """Test deleting a non-existing user."""

    response = client.delete("/users/foo-bar-baz-qux", headers=steward_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


def test_delete_user_as_data_steward(client_with_db, user_headers, steward_headers):
    """Test that a registered user can be deleted by a data steward."""

    user_data = MIN_USER_DATA
    response = client_with_db.post("/users", json=user_data, headers=user_headers)
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()
    id_ = expected_user["id"]

    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()
    assert user["id"] == id_

    response = client_with_db.delete(f"/users/{id_}", headers=steward_headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}

    response = client_with_db.delete(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


def test_delete_user_as_same_user(client):
    """Test that a registered user can be deleted by a data steward."""

    headers = get_headers_for(
        id="some-id", name="Max Headroom", email="max@example.org"
    )
    response = client.delete("/users/some-id", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}

    # even data stewards cannot delete their own accounts
    headers = get_headers_for(
        id="some-id", name="Max Headroom", email="max@example.org", role="data_steward"
    )
    response = client.delete("/users/some-id", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to delete this user."}


def test_delete_user_unauthenticated(client):
    """Test that deleting a user without authentication does not work."""

    response = client.delete("/users/foo-bar-baz-qux")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}
