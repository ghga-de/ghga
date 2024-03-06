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
from typing import cast

from fastapi import status
from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest import mark

from auth_service.user_management.user_registry.utils import is_internal_id

from ....fixtures.utils import get_headers_for
from .fixtures import (  # noqa: F401
    fixture_client,
    fixture_client_with_db,
    fixture_mongodb,
)

pytestmark = mark.asyncio()


MIN_USER_DATA = {
    "ext_id": "max@ls.org",
    "name": "Max Headroom",
    "email": "max@example.org",
}

OPT_USER_DATA = {
    "title": "Dr.",
}

MAX_USER_DATA = {**MIN_USER_DATA, **OPT_USER_DATA}

DUMMY_USER_ID = "12345678-9012-3456-7890-123456789012"


def seconds_passed(date_string: str) -> float:
    """Get number of seconds that have passed since the given date string."""
    return (
        cast(datetime, now_as_utc())
        - datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    ).total_seconds()


async def test_health_check(client):
    """Test that the health check endpoint works."""
    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


async def test_get_from_a_random_path(client):
    """Test that a GET request to a random path raises a not found error."""
    response = await client.post("/some/random/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_post_user(client_with_db, new_user_headers):
    """Test that registering a user works."""
    user_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()

    id_ = user.pop("id", None)
    assert is_internal_id(id_)

    assert user.pop("status") == "active"
    assert user.pop("status_change") is None
    assert 0 <= seconds_passed(user.pop("registration_date")) <= 10

    assert user.pop("active_submissions") == []
    assert user.pop("active_access_requests") == []

    assert user == user_data

    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    error = response.json()
    assert error == {"detail": "User was already registered."}


async def test_post_user_with_minimal_data(client_with_db, new_user_headers):
    """Test that registering a user with minimal data works."""
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()

    id_ = user.pop("id", None)
    assert is_internal_id(id_)

    assert user.pop("status") == "active"
    assert user.pop("status_change") is None
    assert 0 <= seconds_passed(user.pop("registration_date")) <= 10

    assert user.pop("active_submissions") == []
    assert user.pop("active_access_requests") == []

    assert user == {**MIN_USER_DATA, **dict.fromkeys(OPT_USER_DATA)}

    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    error = response.json()
    assert error == {"detail": "User was already registered."}


async def test_post_user_with_status(client_with_db, new_user_headers):
    """Test that status field is rejected when registering a user."""
    user_data = {**MIN_USER_DATA, "status": "active"}
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_post_user_with_different_name(client, new_user_headers):
    """Test that registering a user with different name does not work."""
    user_data = {**MAX_USER_DATA, "name": "Max Liebermann"}
    response = await client.post("/users", json=user_data, headers=new_user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert error["detail"] == "User cannot be registered."


async def test_post_user_with_different_email(client, new_user_headers):
    """Test that registering a user with different email does not work."""
    user_data = {**MAX_USER_DATA, "email": "max@fake.org"}
    response = await client.post("/users", json=user_data, headers=new_user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert error["detail"] == "User cannot be registered."


async def test_post_user_with_invalid_email(client, new_user_headers):
    """Test that registering a user with invalid email does not work."""
    user_data = {**MAX_USER_DATA, "email": "invalid"}
    response = await client.post("/users", json=user_data, headers=new_user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "The email address is not valid." in error["detail"][0]["msg"]


async def test_post_user_with_different_ext_id(client, new_user_headers):
    """Test that registering a user with a different external ID does not work."""
    user_data = {**MAX_USER_DATA, "ext_id": "frodo@ls.org"}
    response = await client.post("/users", json=user_data, headers=new_user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authorized to register user."


async def test_post_user_with_existing_user(client, user_headers):
    """Test that registering a user with an internal ID does not work."""
    # actually it's not even possible to specify an internal address here
    user_data = {**MAX_USER_DATA, "ext_id": "max-internal"}
    response = await client.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "The email address is not valid." in error["detail"][0]["msg"]


async def test_post_user_unauthenticated(client_with_db):
    """Test that registering a user without authentication does not work."""
    response = await client_with_db.post("/users", json=MAX_USER_DATA)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authenticated"


async def test_put_user(client_with_db, new_user_headers):
    """Test that updating a user works."""
    old_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=old_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    id_ = response.json()["id"]
    assert is_internal_id(id_)

    new_data = {"name": "Max Headhall", "email": "head@example.org", "title": "Prof."}
    for key, value in new_data.items():
        assert value != old_data[key]

    headers = get_headers_for(id=id_, name=new_data["name"], email=new_data["email"])

    response = await client_with_db.put(f"/users/{id_}", json=new_data, headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = await client_with_db.get(f"/users/{id_}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user.pop("id") == id_
    assert user.pop("ext_id") == old_data["ext_id"]
    assert user.pop("status") == "active"
    assert user.pop("status_change") is None
    assert 0 <= seconds_passed(user.pop("registration_date")) <= 10
    assert user.pop("active_submissions") == []
    assert user.pop("active_access_requests") == []

    assert user == new_data


async def test_put_nonexisting_user_with_invalid_id(client_with_db):
    """Test updating a non-existing user with an invalid user ID."""
    user_data = MAX_USER_DATA.copy()
    del user_data["ext_id"]

    id_ = "nonexisting-user-id"
    assert not is_internal_id(id_)
    headers = get_headers_for(id=id_, name=user_data["name"], email=user_data["email"])

    response = await client_with_db.put(
        f"/users/{id_}", json=user_data, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert error["detail"] == "User cannot be updated."


async def test_put_nonexisting_user_with_valid_id(client_with_db):
    """Test updating a non-existing user with a valid user ID."""
    user_data = MAX_USER_DATA.copy()
    del user_data["ext_id"]

    id_ = DUMMY_USER_ID
    headers = get_headers_for(id=id_, name=user_data["name"], email=user_data["email"])

    response = await client_with_db.put(
        f"/users/{id_}", json=user_data, headers=headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error["detail"] == "User does not exist."


async def test_put_user_with_too_much_data(client_with_db):
    """Test that updating a user with too much data does not work."""
    user_data = MAX_USER_DATA
    id_ = "nonexisting-user-id"
    headers = get_headers_for(id=id_, name=user_data["name"], email=user_data["email"])

    response = await client_with_db.put(
        f"/users/{id_}", json=user_data, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "Extra inputs are not permitted" in error["detail"][0]["msg"]


async def test_put_user_with_invalid_data(client_with_db):
    """Test that updating a user with invalid email does not work."""
    user_data = MAX_USER_DATA.copy()
    del user_data["ext_id"]
    id_ = "nonexisting-user-id"
    headers = get_headers_for(id=id_, name=user_data["name"], email=user_data["email"])

    user_data["email"] = "invalid"

    response = await client_with_db.put(
        f"/users/{id_}", json=user_data, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "email address is not valid" in error["detail"][0]["msg"]


async def test_put_user_unauthenticated(client_with_db):
    """Test that updating a user without authentication does not work."""
    response = await client_with_db.put(
        "/users/nonexisting-user-id", json=MAX_USER_DATA
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authenticated"


async def test_get_non_existing_user(client_with_db, steward_headers):
    """Test requesting a non-existing user."""
    response = await client_with_db.get(
        f"/users/{DUMMY_USER_ID}", headers=steward_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


async def test_get_different_user(client, user_headers):
    """Test requesting a different user."""
    response = await client.get("/users/fred-internal", headers=user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to request user."}


async def test_get_user_via_id(client_with_db, new_user_headers, user_headers):
    """Test that a registered user can be found via internal ID."""
    user_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()

    id_ = expected_user["id"]
    response = await client_with_db.get(f"/users/{id_}", headers=user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to request user."}

    headers = get_headers_for(id=id_, name="Max Headroom", email="max@example.org")
    response = await client_with_db.get(f"/users/{id_}", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user == expected_user


async def test_get_user_via_ext_id(client_with_db, new_user_headers, user_headers):
    """Test that a registered user cannot be found via external ID."""
    user_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED

    id_ = expected_user["ext_id"]
    response = await client_with_db.get(f"/users/{id_}", headers=new_user_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}

    id_ = expected_user["ext_id"]
    response = await client_with_db.get(f"/users/{id_}", headers=user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to request user."}


async def test_get_different_user_as_data_steward(
    client_with_db, new_user_headers, steward_headers
):
    """Test requesting a different user as a data steward."""
    user_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()

    id_ = expected_user["id"]
    response = await client_with_db.get(f"/users/{id_}", headers=steward_headers)

    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user == expected_user


async def test_get_user_unauthenticated(client):
    """Test requesting a user without authentication."""
    response = await client.get("/users/foo-bar-baz-qux")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}


async def test_patch_non_existing_user(client_with_db, steward_headers):
    """Test modifying a non-existing user."""
    update_data = {"title": "Prof."}
    response = await client_with_db.patch(
        f"/users/{DUMMY_USER_ID}", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


async def test_patch_user_as_data_steward(
    client_with_db, new_user_headers, steward_headers
):
    """Test that a data steward can modify a registered user."""
    user_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    expected_user = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    id_ = expected_user["id"]

    assert expected_user["status"] == "active"
    assert expected_user.pop("status_change") is None

    update_data = {"status": "inactive", "title": "Prof."}
    assert expected_user["status"] != update_data["status"]
    assert expected_user["title"] != update_data["title"]
    expected_user.update(update_data)

    response = await client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # request user as data steward to check modification
    response = await client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    # can get status change as data steward
    status_change = user.pop("status_change")
    assert status_change["previous"] == "active"
    assert status_change["by"] == "steve-internal"
    assert status_change["context"] == "manual change"
    assert 0 <= seconds_passed(status_change["change_date"]) <= 10

    assert user == expected_user

    # request user as same user
    headers = get_headers_for(id=id_, name="Max Headroom", email="max@example.org")
    response = await client_with_db.get(f"/users/{id_}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    # cannot get status change as normal user
    assert user.pop("status_change") is None
    assert 0 <= seconds_passed(status_change["change_date"]) <= 10

    assert user == expected_user


async def test_patch_user_partially(client_with_db, new_user_headers, steward_headers):
    """Test that a data steward can modify a registered user partially."""
    user_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()
    id_ = expected_user["id"]

    assert expected_user["status"] == "active"
    assert expected_user.pop("status_change") is None

    update_data = {"status": "inactive"}
    assert expected_user["status"] != update_data["status"]
    expected_user.update(update_data)

    response = await client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = await client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    status_change = user.pop("status_change")
    assert status_change["previous"] == "active"
    assert status_change["by"] == "steve-internal"
    assert status_change["context"] == "manual change"
    assert 0 <= seconds_passed(status_change["change_date"]) <= 10

    assert user == expected_user

    update_data = {"title": "Prof."}
    assert expected_user["title"] != update_data["title"]
    expected_user.update(update_data)

    response = await client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = await client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()

    assert user.pop("status_change") == status_change

    assert user == expected_user


async def test_patch_user_as_same_user(
    client_with_db, new_user_headers, steward_headers
):
    """Test that users can modify their title, but not their status."""
    user_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()
    id_ = expected_user["id"]

    # check that users cannot change their own status
    update_data = {"status": "inactive"}
    assert expected_user["status"] != update_data["status"]
    headers = get_headers_for(id=id_, name="Max Headroom", email="max@example.org")
    response = await client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to make this modification."}
    # check that they cannot even change their status as data stewards
    headers = get_headers_for(
        id=id_, name="Max Headroom", email="max@example.org", role="data_steward"
    )
    response = await client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to make this modification."}

    response = await client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()
    assert user == expected_user

    # check that users can change their title
    update_data = {"title": "Prof."}
    assert expected_user["title"] != update_data["title"]
    expected_user.update(update_data)
    headers = get_headers_for(id=id_, name="Max Headroom", email="max@example.org")
    response = await client_with_db.patch(
        f"/users/{id_}", json=update_data, headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = await client_with_db.get(f"/users/{id_}", headers=steward_headers)

    assert response.status_code == status.HTTP_200_OK
    user = response.json()
    assert user == expected_user


async def test_patch_different_user_as_normal_user(client, user_headers):
    """Test that normal users cannot modify other users."""
    update_data = {"title": "Prof."}
    response = await client.patch(
        "/users/somebody-else", json=update_data, headers=user_headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to make this modification."}


async def test_patch_user_unauthenticated(client):
    """Test that modifying a user without authentication does not work."""
    update_data = {"title": "Prof."}
    response = await client.patch(f"/users/{DUMMY_USER_ID}", json=update_data)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}


async def test_delete_non_existing_user(client_with_db, steward_headers):
    """Test deleting a non-existing user."""
    response = await client_with_db.delete(
        f"/users/{DUMMY_USER_ID}", headers=steward_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


async def test_delete_user_as_data_steward(
    client_with_db, new_user_headers, steward_headers
):
    """Test that a registered user can be deleted by a data steward."""
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    expected_user = response.json()
    id_ = expected_user["id"]

    response = await client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_200_OK
    user = response.json()
    assert user["id"] == id_

    response = await client_with_db.delete(f"/users/{id_}", headers=steward_headers)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    response = await client_with_db.get(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}

    response = await client_with_db.delete(f"/users/{id_}", headers=steward_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


async def test_delete_user_as_same_user(client):
    """Test that a registered user can be deleted by a data steward."""
    headers = get_headers_for(
        id="some-id", name="Max Headroom", email="max@example.org"
    )
    response = await client.delete("/users/some-id", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized"}

    # even data stewards cannot delete their own accounts
    headers = get_headers_for(
        id="some-id", name="Max Headroom", email="max@example.org", role="data_steward"
    )
    response = await client.delete("/users/some-id", headers=headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to delete this user."}


async def test_delete_user_unauthenticated(client):
    """Test that deleting a user without authentication does not work."""
    response = await client.delete(f"/users/{DUMMY_USER_ID}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}
