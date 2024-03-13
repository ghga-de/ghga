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
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest import mark

from auth_service.user_management.user_registry.core.registry import UserRegistry

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

VERIFICATION_CODE_SIZE = 6  # the expected size of verification codes


def seconds_passed(date_string: str) -> float:
    """Get number of seconds that have passed since the given date string."""
    return (
        cast(datetime, now_as_utc())
        - datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    ).total_seconds()


async def test_health_check(client: AsyncTestClient):
    """Test that the health check endpoint works."""
    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


async def test_get_from_a_random_path(client: AsyncTestClient):
    """Test that a GET request to a random path raises a not found error."""
    response = await client.post("/some/random/path")

    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_post_user(
    client_with_db: AsyncTestClient, new_user_headers: dict[str, str]
):
    """Test that registering a user works."""
    user_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()

    id_ = user.pop("id", None)
    assert UserRegistry.is_internal_user_id(id_)

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


async def test_post_user_with_minimal_data(
    client_with_db: AsyncTestClient, new_user_headers: dict[str, str]
):
    """Test that registering a user with minimal data works."""
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()

    id_ = user.pop("id", None)
    assert UserRegistry.is_internal_user_id(id_)

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


async def test_post_user_with_status(
    client_with_db: AsyncTestClient, new_user_headers: dict[str, str]
):
    """Test that status field is rejected when registering a user."""
    user_data = {**MIN_USER_DATA, "status": "active"}
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_post_user_with_different_name(
    client: AsyncTestClient, new_user_headers: dict[str, str]
):
    """Test that registering a user with different name does not work."""
    user_data = {**MAX_USER_DATA, "name": "Max Liebermann"}
    response = await client.post("/users", json=user_data, headers=new_user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert error["detail"] == "User cannot be registered."


async def test_post_user_with_different_email(
    client: AsyncTestClient, new_user_headers: dict[str, str]
):
    """Test that registering a user with different email does not work."""
    user_data = {**MAX_USER_DATA, "email": "max@fake.org"}
    response = await client.post("/users", json=user_data, headers=new_user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert error["detail"] == "User cannot be registered."


async def test_post_user_with_invalid_email(
    client: AsyncTestClient, new_user_headers: dict[str, str]
):
    """Test that registering a user with invalid email does not work."""
    user_data = {**MAX_USER_DATA, "email": "invalid"}
    response = await client.post("/users", json=user_data, headers=new_user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "The email address is not valid." in error["detail"][0]["msg"]


async def test_post_user_with_different_ext_id(
    client: AsyncTestClient, new_user_headers: dict[str, str]
):
    """Test that registering a user with a different external ID does not work."""
    user_data = {**MAX_USER_DATA, "ext_id": "frodo@ls.org"}
    response = await client.post("/users", json=user_data, headers=new_user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authorized to register user."


async def test_post_user_with_existing_user(
    client: AsyncTestClient, user_headers: dict[str, str]
):
    """Test that registering a user with an internal ID does not work."""
    # actually it's not even possible to specify an internal address here
    user_data = {**MAX_USER_DATA, "ext_id": "max-internal"}
    response = await client.post("/users", json=user_data, headers=user_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "The email address is not valid." in error["detail"][0]["msg"]


async def test_post_user_unauthenticated(client_with_db: AsyncTestClient):
    """Test that registering a user without authentication does not work."""
    response = await client_with_db.post("/users", json=MAX_USER_DATA)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authenticated"


async def test_put_user(
    client_with_db: AsyncTestClient, new_user_headers: dict[str, str]
):
    """Test that updating a user works."""
    old_data = MAX_USER_DATA
    response = await client_with_db.post(
        "/users", json=old_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    id_ = response.json()["id"]
    assert UserRegistry.is_internal_user_id(id_)

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


async def test_put_non_existing_user_with_invalid_id(client_with_db: AsyncTestClient):
    """Test updating a non-existing user with an invalid user ID."""
    user_data = MAX_USER_DATA.copy()
    del user_data["ext_id"]

    id_ = "non-existing-user-id"
    assert not UserRegistry.is_internal_user_id(id_)
    headers = get_headers_for(id=id_, name=user_data["name"], email=user_data["email"])

    response = await client_with_db.put(
        f"/users/{id_}", json=user_data, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert error["detail"] == "User cannot be updated."


async def test_put_non_existing_user_with_valid_id(client_with_db: AsyncTestClient):
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


async def test_put_user_with_too_much_data(client_with_db: AsyncTestClient):
    """Test that updating a user with too much data does not work."""
    user_data = MAX_USER_DATA
    id_ = "non-existing-user-id"
    headers = get_headers_for(id=id_, name=user_data["name"], email=user_data["email"])

    response = await client_with_db.put(
        f"/users/{id_}", json=user_data, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "Extra inputs are not permitted" in error["detail"][0]["msg"]


async def test_put_user_with_invalid_data(client_with_db: AsyncTestClient):
    """Test that updating a user with invalid email does not work."""
    user_data = MAX_USER_DATA.copy()
    del user_data["ext_id"]
    id_ = "non-existing-user-id"
    headers = get_headers_for(id=id_, name=user_data["name"], email=user_data["email"])

    user_data["email"] = "invalid"

    response = await client_with_db.put(
        f"/users/{id_}", json=user_data, headers=headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error = response.json()
    assert "email address is not valid" in error["detail"][0]["msg"]


async def test_put_user_unauthenticated(client_with_db: AsyncTestClient):
    """Test that updating a user without authentication does not work."""
    response = await client_with_db.put(
        "/users/non-existing-user-id", json=MAX_USER_DATA
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authenticated"


async def test_get_non_existing_user(
    client_with_db: AsyncTestClient, steward_headers: dict[str, str]
):
    """Test requesting a non-existing user."""
    response = await client_with_db.get(
        f"/users/{DUMMY_USER_ID}", headers=steward_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


async def test_get_different_user(
    client: AsyncTestClient, user_headers: dict[str, str]
):
    """Test requesting a different user."""
    response = await client.get("/users/fred-internal", headers=user_headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to request user."}


async def test_get_user_via_id(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    user_headers: dict[str, str],
):
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


async def test_get_user_via_ext_id(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    user_headers: dict[str, str],
):
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
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
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


async def test_get_user_unauthenticated(client: AsyncTestClient):
    """Test requesting a user without authentication."""
    response = await client.get("/users/foo-bar-baz-qux")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}


async def test_patch_non_existing_user(
    client_with_db: AsyncTestClient, steward_headers: dict[str, str]
):
    """Test modifying a non-existing user."""
    update_data = {"title": "Prof."}
    response = await client_with_db.patch(
        f"/users/{DUMMY_USER_ID}", json=update_data, headers=steward_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


async def test_patch_user_as_data_steward(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
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


async def test_patch_user_partially(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
):
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
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
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


async def test_patch_different_user_as_normal_user(
    client: AsyncTestClient, user_headers: dict[str, str]
):
    """Test that normal users cannot modify other users."""
    update_data = {"title": "Prof."}
    response = await client.patch(
        "/users/somebody-else", json=update_data, headers=user_headers
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to make this modification."}


async def test_patch_user_unauthenticated(client: AsyncTestClient):
    """Test that modifying a user without authentication does not work."""
    update_data = {"title": "Prof."}
    response = await client.patch(f"/users/{DUMMY_USER_ID}", json=update_data)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}


async def test_delete_non_existing_user(
    client_with_db: AsyncTestClient, steward_headers: dict[str, str]
):
    """Test deleting a non-existing user."""
    response = await client_with_db.delete(
        f"/users/{DUMMY_USER_ID}", headers=steward_headers
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The user was not found."}


async def test_delete_user_as_data_steward(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
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


async def test_delete_user_as_same_user(client: AsyncTestClient):
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


async def test_delete_user_unauthenticated(client: AsyncTestClient):
    """Test that deleting a user without authentication does not work."""
    response = await client.delete(f"/users/{DUMMY_USER_ID}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}


async def test_crud_operations_for_ivas(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
):
    """Test all CRUD operations for IVAs."""
    # Create a user
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()
    user_id = user["id"]

    headers = get_headers_for(id=user_id, name=user["name"], email=user["email"])

    # Create two IVAs
    data = {"type": "Phone", "value": "123"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    iva_id = response.json()
    assert isinstance(iva_id, dict)
    assert list(iva_id) == ["id"]
    iva_id_phone = iva_id["id"]
    assert iva_id_phone

    data = {"type": "Fax", "value": "456"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    iva_id = response.json()
    assert isinstance(iva_id, dict)
    assert list(iva_id) == ["id"]
    iva_id_fax = iva_id["id"]
    assert iva_id_fax

    # Retrieve the IVAs
    response = await client_with_db.get(f"/users/{user_id}/ivas", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert len(ivas) == 2

    ivas.sort(key=lambda iva: iva["value"])
    for iva in ivas:
        for date_field in ("created", "changed"):
            assert 0 <= seconds_passed(iva.pop(date_field)) <= 10
    assert ivas == [
        {
            "id": iva_id_phone,
            "type": "Phone",
            "value": "123",
            "state": "Unverified",
        },
        {
            "id": iva_id_fax,
            "type": "Fax",
            "value": "456",
            "state": "Unverified",
        },
    ]

    # Delete one IVA
    response = await client_with_db.delete(
        f"/users/{user_id}/ivas/{iva_id_fax}", headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # Check that only the other IVA is left
    response = await client_with_db.get(f"/users/{user_id}/ivas", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert len(ivas) == 1
    assert ivas[0]["id"] == iva_id_phone

    # Delete the remaining IVA
    response = await client_with_db.delete(
        f"/users/{user_id}/ivas/{iva_id_phone}", headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # Check that no IVA is left
    response = await client_with_db.get(f"/users/{user_id}/ivas", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert not ivas


async def test_crud_operations_for_ivas_as_data_steward(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
):
    """Test all CRUD operations for IVAs as a data steward."""
    # Create a user
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()
    user_id = user["id"]

    # Create an IVA
    data = {"type": "Phone", "value": "123/456"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=steward_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    iva_id_obj = response.json()
    assert isinstance(iva_id_obj, dict)
    assert list(iva_id_obj) == ["id"]
    iva_id = iva_id_obj["id"]
    assert iva_id

    # Retrieve the IVA
    response = await client_with_db.get(
        f"/users/{user_id}/ivas", headers=steward_headers
    )
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert len(ivas) == 1

    iva = ivas[0]
    for date_field in ("created", "changed"):
        assert 0 <= seconds_passed(iva.pop(date_field)) <= 10
    assert iva == {
        "id": iva_id,
        "type": "Phone",
        "value": "123/456",
        "state": "Unverified",
    }

    # Delete the IVA
    response = await client_with_db.delete(
        f"/users/{user_id}/ivas/{iva_id}", headers=steward_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # Check that no IVA is left
    response = await client_with_db.get(
        f"/users/{user_id}/ivas", headers=steward_headers
    )
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert not ivas


async def test_crud_operations_for_ivas_as_another_user(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    user_headers: dict[str, str],
    steward_headers: dict[str, str],
):
    """Test that all CRUD operations for IVAs with a different user fail."""
    # Create a user
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()
    user_id = user["id"]

    # Create an IVA
    data = {"type": "InPerson", "value": "Hi there!"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authorized to create this IVA."
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=steward_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    iva_id = response.json()["id"]
    assert iva_id

    # Retrieve the IVA
    response = await client_with_db.get(f"/users/{user_id}/ivas", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authorized to request these IVAs."
    response = await client_with_db.get(
        f"/users/{user_id}/ivas", headers=steward_headers
    )
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert len(ivas) == 1
    assert ivas[0]["id"] == iva_id

    # Delete the IVA
    response = await client_with_db.delete(
        f"/users/{user_id}/ivas/{iva_id}", headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authorized to delete this IVA."
    response = await client_with_db.delete(
        f"/users/{user_id}/ivas/{iva_id}", headers=steward_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Check that no IVA is left
    response = await client_with_db.get(f"/users/{user_id}/ivas", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error["detail"] == "Not authorized to request these IVAs."
    response = await client_with_db.get(
        f"/users/{user_id}/ivas", headers=steward_headers
    )
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert not ivas


async def test_create_iva_for_non_existing_user_as_data_steward(
    client_with_db: AsyncTestClient,
    steward_headers: dict[str, str],
):
    """Test creating an IVA for a non-existing user as a data steward."""
    data = {"type": "InPerson", "value": "Hi there!"}
    response = await client_with_db.post(
        "/users/non-existing-user-id/ivas", json=data, headers=steward_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error["detail"] == "The user was not found."


async def test_get_ivas_for_non_existing_user_as_data_steward(
    client_with_db: AsyncTestClient,
    steward_headers: dict[str, str],
):
    """Test getting all IVAs of a non-existing user as a data steward."""
    response = await client_with_db.get(
        "/users/non-existing-user-id/ivas", headers=steward_headers
    )
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert not ivas


async def test_deleting_iva_for_non_existing_user_as_data_steward(
    client_with_db: AsyncTestClient,
    steward_headers: dict[str, str],
):
    """Test deleting an IVA for a non-existing user as a data steward."""
    response = await client_with_db.delete(
        "/users/non-existing-user-id/ivas/non-existing-iva-id", headers=steward_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error["detail"] == "The IVA was not found."


async def test_deleting_non_existing_iva_for_existing_user_as_data_steward(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
):
    """Test deleting a non-existing IVA for an existing user as a data steward."""
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    user_id = response.json()["id"]
    response = await client_with_db.delete(
        f"/users/{user_id}/ivas/non-existing-iva-id", headers=steward_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error["detail"] == "The IVA was not found."


async def test_happy_path_for_verifying_an_iva(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
):
    """Test the happy path for the creation and verification of an IVA."""
    # Create a user
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()
    user_id = user["id"]

    headers = get_headers_for(id=user_id, name=user["name"], email=user["email"])

    # Create an IVA
    data = {"type": "Phone", "value": "123"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    iva_id = response.json()["id"]
    assert iva_id

    # Request code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/request-code", headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # Create code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/create-code", headers=steward_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    response_obj = response.json()
    assert isinstance(response_obj, dict)
    assert list(response_obj) == ["verification_code"]
    code = response_obj["verification_code"]
    assert isinstance(code, str)
    assert code.isascii()
    assert code.isalnum()
    assert code.isupper()
    assert len(code) == VERIFICATION_CODE_SIZE

    # Transmit code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/code-transmitted", headers=steward_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # Validate code
    data = {"verification_code": code}
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/validate-code", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text

    # Check that the IVA has really been verified
    response = await client_with_db.get(f"/users/{user_id}/ivas", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva["id"] == iva_id
    assert iva["type"] == "Phone"
    assert iva["value"] == "123"
    assert iva["state"] == "Verified"


async def test_user_iva_operations_without_authorization(
    client_with_db: AsyncTestClient,
):
    """Test that IVA operations fail if the user is not authorized."""
    # Request code
    response = await client_with_db.post("/rpc/ivas/some-iva-id/request-code")
    # Note: This should actually return status code 401.
    # This is a known issue in FastAPI and should be fixed there,
    # or a workaround should be implemented in service-commons.
    # See https://github.com/tiangolo/fastapi/discussions/9130
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}
    # Validate code
    data = {"verification_code": "123456"}
    response = await client_with_db.post(
        "/rpc/ivas/some-iva-id/validate-code", json=data
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authenticated"}


async def test_data_steward_iva_operations_without_authorization(
    client_with_db: AsyncTestClient,
    user_headers: dict[str, str],
    new_user_headers: dict[str, str],
):
    """Test that data steward IVA operations fail if the user is not a data steward."""
    # Create a user
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()
    user_id = user["id"]

    headers = get_headers_for(id=user_id, name=user["name"], email=user["email"])

    # Create an IVA as the wrong user
    data = {"type": "Phone", "value": "123"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=user_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized to create this IVA."}

    # Now create it as the proper user
    data = {"type": "Phone", "value": "123"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    iva_id = response.json()["id"]
    assert iva_id

    # Create code as the user who is not a data steward
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/create-code", headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized"}

    # Transmit code as the user who is not a data steward
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/code-transmitted", headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized"}

    # Validate code as the wrong user
    data = {"verification_code": "123456"}
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/validate-code", json=data, headers=user_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = response.json()
    assert error == {"detail": "The IVA was not found."}

    # Validate code as the proper user, but code has not been requested
    data = {"verification_code": "123456"}
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/validate-code", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    error = response.json()
    assert error == {"detail": "The IVA does not have the proper state."}

    # Unverify IVA as the user who is not a data steward
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/unverify", headers=headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    error = response.json()
    assert error == {"detail": "Not authorized"}


async def test_wrongly_verifying_a_few_times(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
):
    """Test that that a few failed attempts to verify an IVA are tolerated."""
    # Create a user
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()
    user_id = user["id"]

    headers = get_headers_for(id=user_id, name=user["name"], email=user["email"])

    # Create an IVA
    data = {"type": "Phone", "value": "123"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    iva_id = response.json()["id"]
    assert iva_id
    # Request code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/request-code", headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Create code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/create-code", headers=steward_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    code = response.json()["verification_code"]
    assert code
    assert isinstance(code, str)
    assert code.isascii()
    assert code.isalnum()
    assert code.isupper()
    assert len(code) == VERIFICATION_CODE_SIZE
    # Transmit code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/code-transmitted", headers=steward_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Send wrong verification code 9 times
    last_char_is_digit = code[-1].isdigit()
    wrong_last_chars = "ABCDEFGHI" if last_char_is_digit else "123456789"
    for i in range(9):
        invalid_code = code[:-1] + wrong_last_chars[i]
        data = {"verification_code": invalid_code}
        response = await client_with_db.post(
            f"/rpc/ivas/{iva_id}/validate-code", json=data, headers=headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        error = response.json()
        assert error == {"detail": "The submitted verification code was invalid."}
    # Now send right verification code, this time it should succeed
    data = {"verification_code": code}
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/validate-code", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Check that the IVA has really been verified
    response = await client_with_db.get(f"/users/{user_id}/ivas", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva["id"] == iva_id
    assert iva["state"] == "Verified"


async def test_wrongly_verifying_an_iva_too_often(
    client_with_db: AsyncTestClient,
    new_user_headers: dict[str, str],
    steward_headers: dict[str, str],
):
    """Test that too many failed attempts to verify an IVA will reset it."""
    # Create a user
    user_data = MIN_USER_DATA
    response = await client_with_db.post(
        "/users", json=user_data, headers=new_user_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    user = response.json()
    user_id = user["id"]

    headers = get_headers_for(id=user_id, name=user["name"], email=user["email"])

    # Create an IVA
    data = {"type": "Phone", "value": "123"}
    response = await client_with_db.post(
        f"/users/{user_id}/ivas", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    iva_id = response.json()["id"]
    assert iva_id
    # Request code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/request-code", headers=headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Create code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/create-code", headers=steward_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    code = response.json()["verification_code"]
    assert code
    assert isinstance(code, str)
    assert code.isascii()
    assert code.isalnum()
    assert code.isupper()
    assert len(code) == VERIFICATION_CODE_SIZE
    # Transmit code
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/code-transmitted", headers=steward_headers
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Send wrong verification code 10 times
    last_char_is_digit = code[-1].isdigit()
    wrong_last_chars = "ABCDEFGHIJ" if last_char_is_digit else "0123456789"
    for i in range(10):
        invalid_code = code[:-1] + wrong_last_chars[i]
        data = {"verification_code": invalid_code}
        response = await client_with_db.post(
            f"/rpc/ivas/{iva_id}/validate-code", json=data, headers=headers
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        error = response.json()
        assert error == {"detail": "The submitted verification code was invalid."}
    # Now send right verification code, but it's not accepted anymore
    data = {"verification_code": code}
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/validate-code", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    error = response.json()
    assert error == {"detail": "Too many attempts, IVA was reset to unverified state."}
    # Try yet another time, but the state has been reset now
    data = {"verification_code": code}
    response = await client_with_db.post(
        f"/rpc/ivas/{iva_id}/validate-code", json=data, headers=headers
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    error = response.json()
    assert error == {"detail": "The IVA does not have the proper state."}

    # Check that the IVA has really not been verified
    response = await client_with_db.get(f"/users/{user_id}/ivas", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    ivas = response.json()
    assert isinstance(ivas, list)
    assert len(ivas) == 1
    iva = ivas[0]
    assert iva["id"] == iva_id
    assert iva["state"] == "Unverified"
